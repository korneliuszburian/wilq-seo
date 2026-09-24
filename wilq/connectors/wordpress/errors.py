"""Shared, sanitized WordPress read error contracts."""


class WordPressDraftReadError(RuntimeError):
    def __init__(self, public_message: str) -> None:
        super().__init__(public_message)
        self.public_message = public_message
