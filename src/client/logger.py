"""Связь"""
import logging

def setup_logger():
    logger = logging.getLogger("CLIENT")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()   # ТОЛЬКО терминал
    formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger
