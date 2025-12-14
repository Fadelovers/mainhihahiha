from dataclasses import dataclass
from typing import Tuple, Optional
import json


@dataclass
class RestrictedZone:
    """ Описание зоны на карте, в которой запрещены снимки.
        Имеет прямоугольную форму и задается двумя точками на карте

        (lat_bot_left, lon_bot_left) и (lat_top_right, lon_top_right) """
    lat_bot_left: float
    lon_bot_left: float
    lat_top_right: float
    lon_top_right: float
    zone_id: int
    description: str = ""
    severity_level: int = 1  # Уровень серьезности: 1-низкий, 2-средний, 3-высокий

    def __init__(self, zone_id, lat_bot_left, lon_bot_left, lat_top_right, lon_top_right,
                 description="", severity_level=1):
        # Проверяем корректность координат
        if not (-90 <= lat_bot_left <= 90 and -90 <= lat_top_right <= 90):
            raise ValueError("Широта должна быть в диапазоне [-90, 90]")
        if not (-180 <= lon_bot_left <= 180 and -180 <= lon_top_right <= 180):
            raise ValueError("Долгота должна быть в диапазоне [-180, 180]")

        # Убеждаемся, что нижний левый угол действительно ниже и левее верхнего правого
        if lat_bot_left >= lat_top_right:
            raise ValueError(
                f"Некорректные широты: нижняя граница {lat_bot_left} должна быть меньше верхней {lat_top_right}")

        # Для долготы учитываем переход через 180/-180
        # Приводим долготы к диапазону [0, 360) для корректного сравнения
        lon1_normalized = (lon_bot_left + 360) % 360
        lon2_normalized = (lon_top_right + 360) % 360

        if lon1_normalized >= lon2_normalized:
            # Для зон, пересекающих линию смены дат, нужно специальное обращение
            # Пока просто запретим такие зоны для простоты
            raise ValueError(
                f"Некорректные долготы: левая граница {lon_bot_left} должна быть меньше правой {lon_top_right}")

        if not (1 <= severity_level <= 3):
            raise ValueError("Уровень серьезности должен быть от 1 до 3")

        self.zone_id = zone_id
        self.lat_bot_left = lat_bot_left
        self.lon_bot_left = lon_bot_left
        self.lat_top_right = lat_top_right
        self.lon_top_right = lon_top_right
        self.description = description
        self.severity_level = severity_level

    def contains(self, lat: float, lon: float) -> bool:
        """Проверяет, находится ли точка внутри запрещенной зоны"""
        # Нормализуем долготы для корректной проверки
        lat_in_range = self.lat_bot_left <= lat <= self.lat_top_right

        # Проверяем долготу с учетом возможного перехода через 180/-180
        lon_normalized = (lon + 360) % 360
        lon_left_normalized = (self.lon_bot_left + 360) % 360
        lon_right_normalized = (self.lon_top_right + 360) % 360

        if lon_left_normalized <= lon_right_normalized:
            # Обычная зона без пересечения линии смены дат
            lon_in_range = lon_left_normalized <= lon_normalized <= lon_right_normalized
        else:
            # Зона пересекает линию смены дат
            lon_in_range = (lon_normalized >= lon_left_normalized) or (lon_normalized <= lon_right_normalized)

        return lat_in_range and lon_in_range

    def get_center(self) -> Tuple[float, float]:
        """Возвращает центр запрещенной зоны"""
        center_lat = (self.lat_bot_left + self.lat_top_right) / 2
        center_lon = (self.lon_bot_left + self.lon_top_right) / 2
        return center_lat, center_lon

    def get_area(self) -> float:
        """Возвращает площадь зоны в квадратных градусах"""
        lat_range = abs(self.lat_top_right - self.lat_bot_left)

        # Для долготы учитываем переход через 180/-180
        lon_left_normalized = (self.lon_bot_left + 360) % 360
        lon_right_normalized = (self.lon_top_right + 360) % 360

        if lon_left_normalized <= lon_right_normalized:
            lon_range = lon_right_normalized - lon_left_normalized
        else:
            lon_range = (360 - lon_left_normalized) + lon_right_normalized

        return lat_range * lon_range

    def get_severity_description(self) -> str:
        """Возвращает текстовое описание уровня серьезности"""
        descriptions = {
            1: "Низкий уровень - информационные ограничения",
            2: "Средний уровень - ограничения для съемки",
            3: "Высокий уровень - полный запрет"
        }
        return descriptions.get(self.severity_level, "Неизвестный уровень")

    def to_dict(self) -> dict:
        """Конвертирует зону в словарь для сериализации"""
        return {
            'zone_id': self.zone_id,
            'lat_bot_left': self.lat_bot_left,
            'lon_bot_left': self.lon_bot_left,
            'lat_top_right': self.lat_top_right,
            'lon_top_right': self.lon_top_right,
            'description': self.description,
            'severity_level': self.severity_level,
            'center': self.get_center(),
            'area': self.get_area(),
            'severity_description': self.get_severity_description()
        }

    def to_json(self) -> str:
        """Конвертирует зону в JSON строку"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'RestrictedZone':
        """Создает зону из словаря"""
        return cls(
            zone_id=data['zone_id'],
            lat_bot_left=data['lat_bot_left'],
            lon_bot_left=data['lon_bot_left'],
            lat_top_right=data['lat_top_right'],
            lon_top_right=data['lon_top_right'],
            description=data.get('description', ''),
            severity_level=data.get('severity_level', 1)
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'RestrictedZone':
        """Создает зону из JSON строки"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def get_bounds(self) -> dict:
        """Возвращает границы зоны в удобном формате"""
        return {
            'north': self.lat_top_right,
            'south': self.lat_bot_left,
            'west': self.lon_bot_left,
            'east': self.lon_top_right
        }

    def intersects(self, other: 'RestrictedZone') -> bool:
        """Проверяет, пересекается ли эта зона с другой зоной"""
        # Проверка по широте
        if (self.lat_top_right < other.lat_bot_left) or (self.lat_bot_left > other.lat_top_right):
            return False

        # Проверка по долготе с учетом перехода через 180/-180
        # Это упрощенная проверка, для полной реализации нужна более сложная логика
        if (self.lon_top_right < other.lon_bot_left) and (self.lon_bot_left > other.lon_top_right):
            return False

        return True

    def __str__(self) -> str:
        """Строковое представление зоны"""
        return (f"RestrictedZone(id={self.zone_id}, "
                f"bounds=[{self.lat_bot_left:.2f}, {self.lon_bot_left:.2f}]->"
                f"[{self.lat_top_right:.2f}, {self.lon_top_right:.2f}], "
                f"severity={self.severity_level}, "
                f"desc='{self.description[:30]}...' if len(self.description) > 30 else self.description)")

    def __repr__(self) -> str:
        return self.__str__()