from enum import IntEnum

class FTPResponseCode(IntEnum):
    """Códigos de respuesta FTP según RFC 959."""
    READY_FOR_NEW_USER = 220
    USER_LOGGED_IN = 230
    PASSWORD_REQUIRED = 331
    PASSIVE_MODE = 227
    FILE_ACTION_COMPLETED = 226
    PATHNAME_CREATED = 257
    BAD_COMMAND = 500
    NOT_LOGGED_IN = 530
    FILE_NOT_FOUND = 550

class TransferMode:
    ACTIVE = "active"
    PASSIVE = "passive"

DEFAULT_BUFFER_SIZE = 4096
DEFAULT_TIMEOUT = 10