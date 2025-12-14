""" Реализация монитора безопасности с поддержкой запрещенных зон """
from multiprocessing import Queue

from src.system.security_monitor import BaseSecurityMonitor
from src.system.queues_dir import QueuesDirectory
from src.system.event_types import Event, ControlEvent
from src.system.config import LOG_ERROR, LOG_DEBUG, LOG_INFO
from src.system.security_policy_type import SecurityPolicy
from src.satellite_control_system.restricted_zone import RestrictedZone
from src.system.config import *


class SecurityMonitorImpl(BaseSecurityMonitor):
    """Реализация монитора безопасности с проверкой запретных зон"""

    def __init__(self, queues_dir: QueuesDirectory, log_level: int):
        super().__init__(queues_dir, log_level)

        # Инициализация политик безопасности
        self._security_policies = [
            SecurityPolicy(source="*", destination="*", operation="*"),
        ]

        # Менеджер запрещенных зон
        self._restricted_zones = {}

        # История нарушений
        self._violations = {}

        self._log_message(LOG_INFO, "Монитор безопасности инициализирован (режим мониторинга)")

    def _check_event(self, event: Event) -> bool:
        """Проверка события"""
        # Разрешаем все события - проверку делаем в _proceed
        return True

    def _proceed(self, event: Event):
        """Обработка разрешенного события с проверкой запретных зон"""

        # Проверяем события о съемке
        if event.operation == 'post_photo_check' or event.operation == 'update_photo_map':
            if event.parameters and isinstance(event.parameters, (tuple, list)) and len(event.parameters) >= 2:
                lat, lon = event.parameters[0], event.parameters[1]

                # Проверяем все зоны
                in_restricted_zone = False
                blocked_zone = None

                for zone in self._restricted_zones.values():
                    if zone.contains(lat, lon):
                        in_restricted_zone = True
                        blocked_zone = zone
                        break

                if in_restricted_zone:
                    # Логируем нарушение
                    user = "unknown"
                    if event.extra_parameters and 'user' in event.extra_parameters:
                        user = event.extra_parameters['user']

                    self._log_message(LOG_ERROR,
                        f"НАРУШЕНИЕ: Пользователь {user} пытается сделать снимок в запретной зоне {blocked_zone.zone_id} ({lat:.2f}, {lon:.2f})")

                    # Увеличиваем счетчик нарушений
                    self._violations[user] = self._violations.get(user, 0) + 1

                    # НЕ отправляем событие дальше - снимок блокируется
                    return
                else:
                    # Если не в запретной зоне - отправляем в отрисовщик
                    q: Queue = self._queues_dir.get_queue(ORBIT_DRAWER_QUEUE_NAME)
                    if q:
                        q.put(Event(
                            source=self._event_source_name,
                            destination=ORBIT_DRAWER_QUEUE_NAME,
                            operation='update_photo_map',
                            parameters=(lat, lon),
                            extra_parameters=event.extra_parameters,
                            signature=event.signature
                        ))
                    return

        # Специальная обработка для команд управления зонами
        elif event.operation == 'add_restricted_zone':
            zone = event.parameters
            if isinstance(zone, RestrictedZone):
                self._restricted_zones[zone.zone_id] = zone
                self._log_message(LOG_INFO, f"Добавлена запрещенная зона {zone.zone_id}")

                # Отправляем зону в отрисовщик для отображения
                q: Queue = self._queues_dir.get_queue(ORBIT_DRAWER_QUEUE_NAME)
                if q:
                    q.put(Event(
                        source=self._event_source_name,
                        destination=ORBIT_DRAWER_QUEUE_NAME,
                        operation='draw_restricted_zone',
                        parameters=zone
                    ))

        elif event.operation == 'remove_restricted_zone':
            zone_id = event.parameters
            if zone_id in self._restricted_zones:
                del self._restricted_zones[zone_id]
                self._log_message(LOG_INFO, f"Удалена запрещенная зона {zone_id}")

                # Отправляем команду в отрисовщик для удаления
                q: Queue = self._queues_dir.get_queue(ORBIT_DRAWER_QUEUE_NAME)
                if q:
                    q.put(Event(
                        source=self._event_source_name,
                        destination=ORBIT_DRAWER_QUEUE_NAME,
                        operation='clear_restricted_zone',
                        parameters=zone_id
                    ))
        else:
            # Стандартная обработка - отправка получателю
            super()._proceed(event)

    def get_violation_stats(self):
        """Получить статистику нарушений"""
        return self._violations.copy()

    def get_restricted_zones_count(self):
        """Получить количество запретных зон"""
        return len(self._restricted_zones)