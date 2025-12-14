"""Менеджер очередей команд"""
import time
from multiprocessing import Queue
from src.system.event_types import Event
from src.system.config import *
from src.satellite_control_system.restricted_zone import RestrictedZone


class InterpreterImpl:
    def __init__(self, user, role, logger, queues_dir):
        self.user = user
        self.role = role
        self.log = logger
        self.queues_dir = queues_dir
        self.command_counter = 0

    def run(self, commands):
        self.log.info(f"Пользователь '{self.user}' начал выполнение программы")

        if not commands:
            self.log.warning("Программа пуста")
            return

        for i, cmd in enumerate(commands, 1):
            self.log.info(f"Обработка команды #{i}: {cmd.name}")

            # Проверка прав доступа
            if not self._is_allowed(cmd.name):
                self.log.warning(f"ЗАПРЕЩЕНО: {cmd.name} - недостаточно прав (роль: {self.role})")
                continue

            try:
                self._execute_command(cmd)
                self.log.info(f"ВЫПОЛНЕНО: {cmd.name} {cmd.args}")

                # Пауза между командами для стабильности
                if cmd.name != "MAKE PHOTO":  # Для фото пауза меньше
                    time.sleep(1.0)
                else:
                    time.sleep(0.5)

            except Exception as e:
                self.log.error(f"Ошибка выполнения команды {cmd.name}: {e}")

        self.log.info("Выполнение программы завершено")

    def _is_allowed(self, command_name):
        """Проверка прав доступа для команды"""
        permissions = {
            "MAKE PHOTO": {1, 2, 3},  # Все могут делать фото
            "ORBIT": {2, 3},  # VIP и админ
            "ADD ZONE": {3},  # Только админ
            "REMOVE ZONE": {3}  # Только админ
        }
        return self.role in permissions.get(command_name, set())

    def _execute_command(self, cmd):
        """Выполнение команды - отправка в соответствующую очередь"""

        if cmd.name == "ORBIT":
            altitude, raan, inclination = cmd.args

            # Проверка корректности параметров
            if not (160000 <= altitude <= 2000000):
                raise ValueError(f"Высота орбиты {altitude} вне допустимого диапазона (160000-2000000)")
            if not (-3.14 <= raan <= 3.14):
                raise ValueError(f"RAAN {raan} вне допустимого диапазона")
            if not (-1.57 <= inclination <= 1.57):
                raise ValueError(f"Наклон {inclination} вне допустимого диапазона")

            # Отправка команды через монитор безопасности
            q = self.queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
            if q:
                event = Event(
                    source=f"client_{self.user}",
                    destination=ORBIT_CONTROL_QUEUE_NAME,
                    operation="change_orbit",
                    parameters=(altitude, raan, inclination),
                    signature=f"orbit_cmd_{self.user}_{self.command_counter}"
                )
                q.put(event)
                self.command_counter += 1

        elif cmd.name == "MAKE PHOTO":
            # Отправка команды через монитор безопасности
            q = self.queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
            if q:
                event = Event(
                    source=f"client_{self.user}",
                    destination=OPTICS_CONTROL_QUEUE_NAME,
                    operation="request_photo",
                    parameters=None,
                    extra_parameters={'priority': 1, 'user': self.user, 'role': self.role},
                    signature=f"photo_cmd_{self.user}_{self.command_counter}"
                )
                q.put(event)
                self.command_counter += 1

        elif cmd.name == "ADD ZONE":
            zone_id, lat1, lon1, lat2, lon2 = cmd.args

            # Создаем объект запрещенной зоны
            zone = RestrictedZone(
                zone_id=zone_id,
                lat_bot_left=min(lat1, lat2),
                lon_bot_left=min(lon1, lon2),
                lat_top_right=max(lat1, lat2),
                lon_top_right=max(lon1, lon2),
                description=f"Добавлено пользователем {self.user}",
                severity_level=3  # Высокий уровень серьезности по умолчанию
            )

            # Отправка команды через монитор безопасности
            q = self.queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
            if q:
                event = Event(
                    source=f"client_{self.user}",
                    destination=SECURITY_MONITOR_QUEUE_NAME,
                    operation="add_restricted_zone",
                    parameters=zone,
                    extra_parameters={'user': self.user, 'role': self.role},
                    signature=f"addzone_cmd_{self.user}_{self.command_counter}"
                )
                q.put(event)
                self.command_counter += 1

        elif cmd.name == "REMOVE ZONE":
            zone_id = cmd.args[0]

            # Отправка команды через монитор безопасности
            q = self.queues_dir.get_queue(SECURITY_MONITOR_QUEUE_NAME)
            if q:
                event = Event(
                    source=f"client_{self.user}",
                    destination=SECURITY_MONITOR_QUEUE_NAME,
                    operation="remove_restricted_zone",
                    parameters=zone_id,
                    extra_parameters={'user': self.user, 'role': self.role},
                    signature=f"removezone_cmd_{self.user}_{self.command_counter}"
                )
                q.put(event)
                self.command_counter += 1

        else:
            raise ValueError(f"Неизвестная команда: {cmd.name}")