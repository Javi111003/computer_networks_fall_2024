class FTPClientError(Exception):
    """Excepción base para errores del cliente FTP."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} - {message}")

class FTPTransferError(FTPClientError):
    """Error durante la transferencia de archivos."""

class FTPAuthError(FTPClientError):
    """Error de autenticación."""

class FTPConnectionError(FTPClientError):
    """Error de conexión con el servidor."""