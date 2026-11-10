class AppError(Exception):
    """Error con mensaje seguro para el usuario (sin rutas privadas)."""

    def __init__(self, message: str, status: int = 400, code: str = "error"):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


class Cancelled(Exception):
    pass
