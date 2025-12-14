"""Модуль связи"""
class Command:
    def __init__(self, name, args=()):
        self.name = name
        self.args = args

def parse_program(path="program.txt"):
    commands = []
    with open(path, "r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue

            parts = s.split()

            if parts[0] == "ORBIT":
                commands.append(Command("ORBIT", tuple(map(float, parts[1:4]))))

            elif s == "MAKE PHOTO":
                commands.append(Command("MAKE PHOTO"))

            elif parts[0] == "ADD" and parts[1] == "ZONE":
                commands.append(Command(
                    "ADD ZONE",
                    (int(parts[2]), *map(float, parts[3:7]))
                ))

            elif parts[0] == "REMOVE" and parts[1] == "ZONE":
                commands.append(Command("REMOVE ZONE", (int(parts[2]),)))

            else:
                raise ValueError(f"Syntax error at line {n}")

    return commands
