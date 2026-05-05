import logging
import random
import time
from typing import Callable
from pynput.keyboard import Controller

logger = logging.getLogger("quill.typer")


class Typer:
    def __init__(
        self,
        min_delay: float = 0.01,
        max_delay: float = 0.03,
        sleeper: Callable[[float], None] | None = None,
    ):
        self._controller = Controller()
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._sleeper = sleeper if sleeper is not None else time.sleep

    def type_text(self, text: str) -> None:
        """Type the given text character by character with random delays.

        This method types each character individually using the keyboard
        controller, simulating human-like typing by sleeping for a random
        duration between characters. Empty strings are handled gracefully
        and result in no-op behavior.

        Args:
            text: The string to type.
        """
        if not text:
            return
        logger.info("Typing %d characters…", len(text))
        for char in text:
            self._controller.type(char)
            self._sleeper(random.uniform(self._min_delay, self._max_delay))
        logger.info("Typing complete")
