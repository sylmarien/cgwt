"""Errors that cgwt reports to the user."""


class CgwtError(Exception):
    """An expected failure.

    The message has the form `<what failed>. <what to run or pass instead>.`
    """

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
