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
    COMMAND_OK = 200
    SYNTAX_ERROR = 501
    COMMAND_NOT_IMPLEMENTED = 502
    BAD_SEQUENCE = 503
    COMMAND_NOT_IMPLEMENTED_FOR_PARAM = 504
    RESTART_MARKER = 110
    SERVICE_READY = 120
    DATA_CONNECTION_ALREADY_OPEN = 125
    FILE_STATUS_OK = 150
    COMMAND_NOT_ACCEPTED = 421
    CANNOT_OPEN_DATA_CONNECTION = 425
    CONNECTION_CLOSED = 426
    ACTION_NOT_TAKEN = 450
    ACTION_ABORTED = 451
    INSUFFICIENT_STORAGE = 452

class TransferMode:
    ACTIVE = "active"
    PASSIVE = "passive"

DEFAULT_BUFFER_SIZE = 4096
DEFAULT_TIMEOUT = 10