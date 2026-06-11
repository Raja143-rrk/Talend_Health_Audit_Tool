import logging

from backend.core.logging import get_logger


def get_agent_logger(agent_name: str) -> logging.Logger:
    return get_logger(f"backend.agents.{agent_name}")
