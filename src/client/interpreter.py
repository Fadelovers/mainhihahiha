"""Интерпретатор"""
from .permissions import allowed

class Interpreter:
    def __init__(self, user, role, logger):
        self.user = user
        self.role = role
        self.log = logger

    def run(self, commands):
        self.log.info(f"User '{self.user}' started program execution")

        if not commands:
            self.log.warning("Program is empty")
            return

        for i, cmd in enumerate(commands, 1):
            self.log.info(f"Processing command #{i}: {cmd.name}")

            if not allowed(self.role, cmd.name):
                self.log.warning(f"DENIED: {cmd.name}")
                continue

            self.log.info(f"ALLOWED: {cmd.name} {cmd.args}")

        self.log.info("Program execution finished")
