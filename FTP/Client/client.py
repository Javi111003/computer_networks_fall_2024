import socket
import re
import argparse
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
            "PWD": self.get_current_dir,
            "CWD": self.change_dir,
            "MKD": self.make_dir,
            "RMD": self.remove_dir,
            "DELE": self.delete_file,
            "RNFR": self.rename_from,
            "RNTO": self.rename_to,
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
        args = tuple(arg for arg in args if arg != "")
        cmd = command.upper()
        if cmd in self.command_dispatcher:
            return self.command_dispatcher[cmd](*args)
        return self.send_command(command, *args)

    def _handle_user(self, username: str) -> str:
        """Maneja el comando USER (inicio de autenticación)."""
        response = self.send_command("USER", username)
        if self._parse_code(response) not in (FTPResponseCode.PASSWORD_REQUIRED, FTPResponseCode.USER_LOGGED_IN):
            raise FTPAuthError(self._parse_code(response), "Usuario inválido")
        return response

    def _handle_pass(self, password: str) -> str:
        """Maneja el comando PASS (finaliza autenticación)."""
        response = self.send_command("PASS", password)
        if FTPResponseCode.USER_LOGGED_IN != self._parse_code(response):
            raise FTPAuthError(self._parse_code(response), "Contraseña inválida")
        return response

    def get_current_dir(self) -> str:
        """Obtiene el directorio actual (PWD)"""
        response = self.send_command("PWD")
        if self._parse_code(response) != FTPResponseCode.PATHNAME_CREATED:
            raise FTPClientError(self._parse_code(response), "Error obteniendo directorio")
        return re.search(r'"(.*)"', response).group(1)

    def change_dir(self, path: str) -> str:
        """Cambia de directorio (CWD)"""
        response = self.send_command("CWD", path)
        if self._parse_code(response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPClientError(self._parse_code(response), "Error cambiando directorio")
        return response

    def make_dir(self, path: str) -> str:
        """Crea un directorio (MKD)"""
        response = self.send_command("MKD", path)
        if self._parse_code(response) != FTPResponseCode.PATHNAME_CREATED:
            raise FTPClientError(self._parse_code(response), "Error creando directorio")
        return response

    def remove_dir(self, path: str) -> str:
        """Elimina un directorio (RMD)"""
        response = self.send_command("RMD", path)
        if self._parse_code(response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPClientError(self._parse_code(response), "Error eliminando directorio")
        return response

    def delete_file(self, filename: str) -> str:
        """Elimina un archivo (DELE)"""
        response = self.send_command("DELE", filename)
        if self._parse_code(response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPClientError(self._parse_code(response), "Error eliminando archivo")
        return response

    def rename_from(self, old_name: str):
        """Prepara renombrado (RNFR)"""
        response = self.send_command("RNFR", old_name)
        if self._parse_code(response) != 350:
            raise FTPClientError(self._parse_code(response), "RNFR fallido")
        #self.rename_from_name = old_name
        return response

    def rename_to(self, new_name: str):
        """Completa renombrado (RNTO)"""
        #if not self.rename_from_name:
        #    raise FTPClientError(503, "Secuencia RNFR/RNTO incorrecta")
        response = self.send_command("RNTO", new_name)
        if self._parse_code(response) not in (FTPResponseCode.FILE_ACTION_COMPLETED, 250):
            raise FTPClientError(self._parse_code(response), "RNTO fallido")
        #self.rename_from_name = ""
        return response

    def rename_file(self, old_name: str, new_name: str):
        """Maneja la secuencia completa RNFR/RNTO"""
        response_from = self.rename_from(old_name)
        response_to = self.rename_to(new_name)
        return response_from + "\n" + response_to

    def download_file(self, remote_path: str, local_path: str = None) -> str:
        """Descarga un archivo usando RETR."""
        # Si no se especifica el archivo local, se utiliza el mismo nombre
        if local_path is None:
            local_path = remote_path

        self._setup_data_connection()

        # Enviar comando RETR
        response = self.send_command("RETR", remote_path)

        if self._parse_code(response) not in (125, 150):
            raise FTPTransferError(self._parse_code(response), "Error en RETR")

        # Recibir el archivo y guardarlo en local
        self._receive_data(local_path)

        # Leer la respuesta final del servidor (por ejemplo, 226)
        final_response = self._get_response()
        if self._parse_code(final_response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPTransferError(self._parse_code(final_response), "Error en RETR final")

        return final_response

    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Sube un archivo usando STOR."""
        self._setup_data_connection()

        response = self.send_command("STOR", remote_path)
        if self._parse_code(response) not in (125, 150):
            raise FTPTransferError(self._parse_code(response), "Error en STOR")

        self._send_data(local_path)
        final_response = self._get_response()
        if self._parse_code(final_response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPTransferError(self._parse_code(final_response), "Error en STOR final")

        return final_response

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
        if self.control_sock:
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
        """Parses the response code from the server."""
        if not response:
            return 0
        lines = response.split("\r\n")
        return int(lines[-1].split()[0]) if lines else 0

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

#---------------#
# FTP Client CLI#
#---------------#
def main():
    parser = argparse.ArgumentParser(description="Cliente FTP", add_help=False)
    parser.add_argument("-h", "--host", required=True, help="Dirección del servidor FTP")
    parser.add_argument("-p", "--port", type=int, default=21, help="Puerto del servidor")
    parser.add_argument("-u", "--user", required=True, help="Nombre de usuario")
    parser.add_argument("-w", "--password", required=True, help="Contraseña")
    parser.add_argument("-c", "--command", required=False, help="Comando FTP a ejecutar")
    parser.add_argument("-a", "--arg1", help="Primer argumento del comando")
    parser.add_argument("-b", "--arg2", help="Segundo argumento del comando")
    parser.add_argument("--help", action="help", default=argparse.SUPPRESS, help="Mostrar este mensaje de ayuda")
    args = parser.parse_args()

    client = FTPClient(host=args.host, port=args.port)
    try:
        # Conexión y autenticación
        client.connect()
        client.execute("USER", args.user)
        client.execute("PASS", args.password)

        if args.command:
            if args.command.upper() in ["RETR", "STOR"]:
                response = client.execute(args.command, args.arg1, args.arg2)
                print(response)
            elif args.command.upper() in ["RNFR", "RNTO"]:
                response = client.rename_file(args.arg1, args.arg2)
                print(response)
            else:
                response = client.execute(args.command, args.arg1 or "")
                print(response)

    except FTPClientError as e:
        print(f"Error: {e}")
    finally:
        if args.command and args.command.upper() != "QUIT":
            client.execute("QUIT")


if __name__ == "__main__":
    main()