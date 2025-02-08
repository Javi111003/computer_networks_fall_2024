import socket
import re
import logging
from typing import Optional, Dict, Callable
from FTP.Common.constants import FTPResponseCode, TransferMode, DEFAULT_BUFFER_SIZE, DEFAULT_TIMEOUT
from FTP.Common.exceptions import FTPClientError, FTPTransferError, FTPAuthError, FTPConnectionError

class FTPClient:
    """Cliente FTP con soporte para modos activo/pasivo y dispatcher de comandos."""

    def __init__(self, host: str, port: int = 21):
        self.host = host
        self.port = port
        self.control_sock: Optional[socket.socket] = None
        self.data_sock: Optional[socket.socket] = None
        self.mode = TransferMode.PASSIVE
        self.logger = logging.getLogger(self.__class__.__name__)
        self.command_dispatcher: Dict[str, Callable] = {
            "USER": self._handle_user,
            "PASS": self._handle_pass,
            "RETR": self.download_file,
            "STOR": self.upload_file,
            "PASV": self.enter_passive_mode,
            "PORT": self.enter_active_mode,
            "QUIT": self.quit
        }

    def connect(self) -> str:
        """Establece conexión inicial con el servidor."""
        try:
            self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_sock.settimeout(DEFAULT_TIMEOUT)
            self.control_sock.connect((self.host, self.port))
            return self._get_response()
        except (socket.error, socket.timeout) as e:
            raise FTPConnectionError(FTPResponseCode.BAD_COMMAND, f"Conexión fallida: {str(e)}")

    def send_command(self, command: str, *args) -> str:
        """Envía un comando genérico al servidor."""
        cmd = f"{command} {' '.join(args)}".strip()
        self.logger.debug(f"Enviando comando: {cmd}")
        self.control_sock.sendall(f"{cmd}\r\n".encode())
        return self._get_response()

    def execute(self, command: str, *args) -> str:
        """Ejecuta un comando usando el dispatcher o envío genérico."""
        cmd = command.upper()
        if cmd in self.command_dispatcher:
            return self.command_dispatcher[cmd](*args)
        return self.send_command(command, *args)

    def _handle_user(self, username: str) -> str:
        """Maneja el comando USER (inicio de autenticación)."""
        response = self.send_command("USER", username)
        if FTPResponseCode.PASSWORD_REQUIRED != self._parse_code(response):
            raise FTPAuthError(self._parse_code(response), "Usuario inválido")
        return response

    def _handle_pass(self, password: str) -> str:
        """Maneja el comando PASS (finaliza autenticación)."""
        response = self.send_command("PASS", password)
        if FTPResponseCode.USER_LOGGED_IN != self._parse_code(response):
            raise FTPAuthError(self._parse_code(response), "Contraseña inválida")
        return response

    def download_file(self, remote_path: str, local_path: str) -> str:
        """Descarga un archivo usando RETR."""
        self._setup_data_connection()

        response = self.send_command("RETR", remote_path)
        if self._parse_code(response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPTransferError(self._parse_code(response), "Error en RETR")

        self._receive_data(local_path)
        return self._get_response()

    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Sube un archivo usando STOR."""
        self._setup_data_connection()

        response = self.send_command("STOR", remote_path)
        if self._parse_code(response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPTransferError(self._parse_code(response), "Error en STOR")

        self._send_data(local_path)
        return self._get_response()

    def enter_passive_mode(self) -> str:
        """Activa modo PASV y configura conexión de datos."""
        response = self.send_command("PASV")
        ip, port = self._parse_pasv_response(response)
        self.data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_sock.connect((ip, port))
        self.mode = TransferMode.PASSIVE
        return response

    def enter_active_mode(self, ip_port: str) -> str:
        """Activa modo PORT (formato: h1,h2,h3,h4,p1,p2)."""
        response = self.send_command("PORT", ip_port)
        self.mode = TransferMode.ACTIVE
        return response

    def quit(self) -> str:
        """Cierra la conexión."""
        response = self.send_command("QUIT")
        self.control_sock.close()
        self._close_data_connection()
        return response

    def _setup_data_connection(self):
        """Prepara conexión según el modo actual."""
        if self.mode == TransferMode.PASSIVE:
            self.enter_passive_mode()
        else:
            # Implementar lógica para modo activo (PORT)
            pass

    def _parse_code(self, response: str) -> int:
        """Extrae el código numérico de la respuesta."""
        return int(response.split()[0]) if response else 0

    def _parse_pasv_response(self, response: str) -> tuple[str, int]:
        """Parsea respuesta PASV (ej: 227 Entering Passive Mode (192,168,1,2,123,45))."""
        match = re.search(r"(\d+,\d+,\d+,\d+),(\d+),(\d+)", response)
        if not match:
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Respuesta PASV inválida")
        ip = match.group(1).replace(",", ".")
        port = (int(match.group(2)) << 8) + int(match.group(3))
        return ip, port

    def _receive_data(self, local_path: str):
        """Recibe datos por el socket de datos y guarda en archivo."""
        try:
            with open(local_path, "wb") as f:
                while True:
                    chunk = self.data_sock.recv(DEFAULT_BUFFER_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
        finally:
            self._close_data_connection()

    def _send_data(self, local_path: str):
        """Envía datos desde un archivo local."""
        try:
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(DEFAULT_BUFFER_SIZE)
                    if not chunk:
                        break
                    self.data_sock.sendall(chunk)
        finally:
            self._close_data_connection()

    def _close_data_connection(self):
        """Cierra el socket de datos."""
        if self.data_sock:
            self.data_sock.close()
            self.data_sock = None

    def _get_response(self) -> str:
        """Lee la respuesta del servidor."""
        response = []
        while True:
            chunk = self.control_sock.recv(DEFAULT_BUFFER_SIZE).decode(errors="ignore")
            if not chunk:
                break
            response.append(chunk)
            if "\r\n" in chunk:
                break
        return "".join(response).strip()