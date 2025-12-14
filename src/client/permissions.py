"""Модуль проверки ограничений"""
ROLE_PHOTO = 1
ROLE_VIP = 2
ROLE_ADMIN = 3

PERMISSIONS = {
    "MAKE PHOTO": {1, 2, 3},
    "ORBIT": {2, 3},
    "ADD ZONE": {3},
    "REMOVE ZONE": {3}
}

def allowed(role: str, command: str) -> bool:
    return role in PERMISSIONS.get(command, set())
