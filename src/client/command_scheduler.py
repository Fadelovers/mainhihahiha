""" Модуль мониторинг """
import threading
import time
from queue import Queue
from typing import List, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.system.event_types import Event
from src.system.queues_dir import QueuesDirectory


@dataclass
class ScheduledCommand:
    """Запланированная команда"""
    time_offset: float  # Время через которое выполнить (секунды от начала)
    command_func: Callable  # Функция для выполнения
    args: tuple
    kwargs: dict


class CommandScheduler:
    """Планировщик команд для системы спутника"""

    def __init__(self, queues_dir: QueuesDirectory):
        self.queues_dir = queues_dir
        self.scheduled_commands: List[ScheduledCommand] = []
        self.start_time = None
        self.running = False
        self.thread = None
        self._lock = threading.Lock()

    def add_command(self, time_offset: float, command_func: Callable, *args, **kwargs):
        """Добавляет команду в расписание"""
        with self._lock:
            self.scheduled_commands.append(
                ScheduledCommand(time_offset, command_func, args, kwargs)
            )
            # Сортируем по времени выполнения
            self.scheduled_commands.sort(key=lambda x: x.time_offset)

    def start(self):
        """Запускает выполнение запланированных команд"""
        self.start_time = time.time()
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

    def stop(self):
        """Останавливает планировщик"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _run_scheduler(self):
        """Основной цикл планировщика"""
        print(f"[SCHEDULER] Запуск планировщика команд")

        executed_commands = set()

        while self.running:
            current_time = time.time()
            elapsed = current_time - self.start_time

            with self._lock:
                for cmd in self.scheduled_commands:
                    # Если время пришло и команда еще не выполнена
                    if elapsed >= cmd.time_offset and cmd not in executed_commands:
                        try:
                            print(f"[SCHEDULER] Выполнение команды через {elapsed:.1f} сек")
                            cmd.command_func(*cmd.args, **cmd.kwargs)
                            executed_commands.add(cmd)
                        except Exception as e:
                            print(f"[SCHEDULER] Ошибка выполнения команды: {e}")

            # Проверяем, все ли команды выполнены
            with self._lock:
                if len(executed_commands) == len(self.scheduled_commands):
                    print("[SCHEDULER] Все команды выполнены")
                    break

            time.sleep(0.1)  # Частота проверки

    def clear(self):
        """Очищает расписание"""
        with self._lock:
            self.scheduled_commands.clear()


# Фабрика команд для удобного использования
class CommandFactory:
    """Фабрика для создания команд"""

    @staticmethod
    def create_orbit_change(queues_dir: QueuesDirectory, altitude: float, raan: float, inclination: float):
        """Создает команду изменения орбиты"""

        def change_orbit():
            sat_q = queues_dir.get_queue("satellite")
            if sat_q:
                sat_q.put(Event(
                    source="scheduler",
                    destination="satellite",
                    operation="change_orbit",
                    parameters=(altitude, raan, inclination)
                ))
                print(f"[SCHEDULER] Отправлена команда изменения орбиты: alt={altitude}")

        return change_orbit

    @staticmethod
    def create_photo_request(queues_dir: QueuesDirectory, count: int = 1, interval: float = 0.2):
        """Создает команду запроса фотографий"""

        def request_photos():
            camera_q = queues_dir.get_queue("camera")
            if camera_q:
                for i in range(count):
                    camera_q.put(Event(
                        source="scheduler",
                        destination="camera",
                        operation="request_photo",
                        parameters=None
                    ))
                    print(f"[SCHEDULER] Запрос фото {i + 1}/{count}")
                    if i < count - 1:  # Не спать после последнего
                        time.sleep(interval)

        return request_photos

    @staticmethod
    def create_zone_add(queues_dir: QueuesDirectory, zone_id: int, lat1: float, lon1: float, lat2: float, lon2: float):
        """Создает команду добавления запретной зоны"""
        from src.satellite_control_system.restricted_zone import RestrictedZone

        def add_zone():
            drawer_q = queues_dir.get_queue("orbit_drawer")
            if drawer_q:
                zone = RestrictedZone(
                    zone_id=zone_id,
                    lat_bot_left=min(lat1, lat2),
                    lon_bot_left=min(lon1, lon2),
                    lat_top_right=max(lat1, lat2),
                    lon_top_right=max(lon1, lon2),
                    description=f"Запланированная зона {zone_id}"
                )
                drawer_q.put(Event(
                    source="scheduler",
                    destination="orbit_drawer",
                    operation="draw_restricted_zone",
                    parameters=zone
                ))
                print(f"[SCHEDULER] Добавлена запретная зона {zone_id}")

        return add_zone

    @staticmethod
    def create_zone_remove(queues_dir: QueuesDirectory, zone_id: int):
        """Создает команду удаления запретной зоны"""

        def remove_zone():
            drawer_q = queues_dir.get_queue("orbit_drawer")
            if drawer_q:
                drawer_q.put(Event(
                    source="scheduler",
                    destination="orbit_drawer",
                    operation="clear_restricted_zone",
                    parameters=zone_id
                ))
                print(f"[SCHEDULER] Удалена запретная зона {zone_id}")

        return remove_zone