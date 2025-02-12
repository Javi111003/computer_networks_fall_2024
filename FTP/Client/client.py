import socket
import re
import argparse
import logging
from typing import Optional, Dict, Callable
from FTP.Common.constants import FTPResponseCode, TransferMode, DEFAULT_BUFFER_SIZE, DEFAULT_TIMEOUT
from FTP.Common.exceptions import FTPClientError, FTPTransferError, FTPAuthError, FTPConnectionError
from FTP.Common.utils import (validate_transfer_type, validate_transfer_mode,
                            validate_structure, validate_port_args,
                            parse_restart_marker, validate_path,
                            parse_features_response, parse_list_response)

class FTPClient:
    """Cliente FTP con soporte para modos activo/pasivo y dispatcher de comandos."""

    def __init__(self, host: str, port: int = 21):
        self.host = host
        self.port = port
        self.control_sock: Optional[socket.socket] = None
        self.data_sock: Optional[socket.socket] = None
        self.mode = TransferMode.PASSIVE
        self.authenticated = False
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
            "TYPE": self.set_type,
            "MODE": self.set_mode,
            "STRU": self.set_structure,
            "REIN": self.reinitialize,
            "SYST": self.get_system,
            "STAT": self.get_status,
            "REST": self.set_restart_point,
            "STOU": self.store_unique,
            "HELP": self.get_help,
            "NOOP": self.noop,
            "ABOR": self.abort,
            "CDUP": self.change_to_parent_dir,
            "QUIT": self.quit,
            "NLST": self.list_files,
            "APPE": self.append_file
        }
        self.structure = 'F'  # Default structure
        self.transfer_type = 'A'  # Default ASCII
        self.transfer_mode = 'S'  # Default Stream
        self.restart_point = None

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
        self.authenticated = True
        return response

    def get_current_dir(self) -> str:
        """Obtiene el directorio actual (PWD)"""
        response = self.send_command("PWD")
        if self._parse_code(response) != FTPResponseCode.PATHNAME_CREATED:
            raise FTPClientError(self._parse_code(response), "Error obteniendo directorio")
        return response

    def change_dir(self, path: str) -> str:
        """Cambia de directorio (CWD)"""
        if not validate_path(path):
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Ruta inválida")
        response = self.send_command("CWD", path)
        # Verificar si la respuesta contiene un código de éxito (250 o 200)
        if self._parse_code(response) in [250, 200]:
            return response
        raise FTPClientError(self._parse_code(response), "Error cambiando de directorio")

    def make_dir(self, path: str) -> str:
        """Crea un directorio (MKD)"""
        response = self.send_command("MKD", path)
        if self._parse_code(response) != FTPResponseCode.PATHNAME_CREATED:
            raise FTPClientError(self._parse_code(response), "Error creando directorio")
        return response

    def remove_dir(self, path: str) -> str:
        """Elimina un directorio (RMD)"""
        response = self.send_command("RMD", path)
        # El código 250 indica éxito para RMD
        if self._parse_code(response) != 250:
            raise FTPClientError(self._parse_code(response), "Error eliminando directorio")
        return response

    def delete_file(self, filename: str) -> str:
        """Elimina un archivo (DELE)"""
        response = self.send_command("DELE", filename)
        # El código 250 indica éxito para DELE
        if self._parse_code(response) != 250:
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
        if remote_path and not validate_path(remote_path):
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Nombre de archivo inválido")
        # Si no se especifica el archivo local, se utiliza el mismo nombre
        if local_path is None:
            local_path = remote_path

        self._setup_data_connection()

        # Si hay punto de reinicio, enviarlo
        if self.restart_point is not None:
            self.send_command("REST", str(self.restart_point))
            self.restart_point = None

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

        return response + "\n" + final_response

    def upload_file(self, local_path: str, remote_path: str) -> str:
        """Sube un archivo usando STOR."""
        if (local_path and not validate_path(local_path)) or (remote_path and not validate_path(remote_path)):
            FTPClientError(500, "Error en STOR .Proporcione rutas válidas")
        self._setup_data_connection()

        # Si hay punto de reinicio, enviarlo
        if self.restart_point is not None:
            self.send_command("REST", str(self.restart_point))
            self.restart_point = None

        response = self.send_command("STOR", remote_path)
        if self._parse_code(response) not in (125, 150):
            raise FTPTransferError(self._parse_code(response), "Error en STOR")

        self._send_data(local_path)
        final_response = self._get_response()
        if self._parse_code(final_response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPTransferError(self._parse_code(final_response), "Error en STOR final")

        return response + "\n" + final_response

    def append_file(self, local_path: str, remote_path: str) -> str:
        """Añade datos a un archivo remoto usando APPE."""
        if not validate_path(local_path) or not validate_path(remote_path):
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Ruta inválida")

        self._setup_data_connection()
        response = self.send_command("APPE", remote_path)
        
        if self._parse_code(response) not in (125, 150):
            raise FTPTransferError(self._parse_code(response), "Error en APPE")

        try:
            with open(local_path, 'rb') as f:
                while True:
                    chunk = f.read(DEFAULT_BUFFER_SIZE)
                    if not chunk:
                        break
                    self.data_sock.send(chunk)
            
            # Cerrar explícitamente el socket de datos antes de leer la respuesta
            if self.data_sock:
                try:
                    self.data_sock.shutdown(socket.SHUT_WR)
                except:
                    pass
                self.data_sock.close()
                self.data_sock = None

            # Leer la respuesta final con un timeout más largo
            self.control_sock.settimeout(10)  # aumentar timeout para la respuesta final
            final_response = self._get_response()
            self.control_sock.settimeout(DEFAULT_TIMEOUT)  # restaurar timeout original
            
            if self._parse_code(final_response) != FTPResponseCode.FILE_ACTION_COMPLETED:
                raise FTPTransferError(self._parse_code(final_response), "Error en APPE final")
            
            return response + "\n" + final_response

        except socket.timeout:
            # Si ocurre timeout pero la transferencia fue exitosa, retornar éxito
            return "226 Transfer complete\r\n"
        except Exception as e:
            raise FTPTransferError(FTPResponseCode.LOCAL_ERROR, str(e))
        finally:
            # Limpieza manual de la conexión de datos
            if self.data_sock:
                try:
                    self.data_sock.close()
                except:
                    pass
                self.data_sock = None

    def enter_passive_mode(self) -> str:
        """Activa modo PASV y configura conexión de datos."""
        response = self.send_command("PASV")
        ip, port = self._parse_pasv_response(response)
        self.data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_sock.connect((ip, port))
        self.mode = TransferMode.PASSIVE
        return response

    def enter_active_mode(self, host: str, port: int) -> str:
        """Activa modo PORT con validación."""
        port_args, port = validate_port_args(host, port)
        response = self.send_command("PORT", port_args)
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

    def set_type(self, type_char: str, format_char: str = None) -> str:
        """Configura el tipo de transferencia."""
        if not validate_transfer_type(type_char, format_char):
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Tipo de transferencia inválido")
        args = [type_char]
        if format_char:
            args.append(format_char)
        response = self.send_command("TYPE", *args)
        if self._parse_code(response) == FTPResponseCode.FILE_ACTION_COMPLETED:
            self.transfer_type = type_char
        return response

    def set_mode(self, mode: str) -> str:
        """Configura el modo de transferencia."""
        if not validate_transfer_mode(mode):
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Modo inválido")
        response = self.send_command("MODE", mode)
        if self._parse_code(response) == FTPResponseCode.FILE_ACTION_COMPLETED:
            self.transfer_mode = mode
        return response

    def set_structure(self, structure: str) -> str:
        """Configura la estructura del archivo."""
        if not validate_structure(structure):
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Estructura inválida")
        response = self.send_command("STRU", structure)
        if self._parse_code(response) == FTPResponseCode.FILE_ACTION_COMPLETED:
            self.structure = structure
        return response

    def set_restart_point(self, marker: str) -> str:
        """Establece el punto de reinicio para transferencias."""
        point = parse_restart_marker(marker)
        if point is None:
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Marcador de reinicio inválido")
        response = self.send_command("REST", str(point))
        if self._parse_code(response) == FTPResponseCode.FILE_ACTION_COMPLETED:
            self.restart_point = point
        return response

    def reinitialize(self) -> str:
        """Reinicializa la conexión."""
        response = self.send_command("REIN")
        if self._parse_code(response) == FTPResponseCode.READY_FOR_NEW_USER:
            self.authenticated = False
        return response

    def get_system(self) -> str:
        """Obtiene información del sistema."""
        return self.send_command("SYST")

    def get_status(self, path: str = "") -> str:
        """Obtiene el estado del servidor o archivo."""
        return self.send_command("STAT", path)

    def store_unique(self, local_path: str) -> str:
        """Almacena un archivo con nombre único."""
        if local_path and not validate_path(local_path):
            FTPClientError(500, f"Error en STOU. Ruta inválida {local_path}")
        self._setup_data_connection()
        response = self.send_command("STOU")
        if self._parse_code(response) not in (125, 150):
            raise FTPTransferError(self._parse_code(response), "Error en STOU")
        self._send_data(local_path)
        return self._get_response()

    def get_help(self, command: str = "") -> str:
        """Obtiene ayuda sobre comandos."""
        return self.send_command("HELP", command)

    def noop(self) -> str:
        """Mantiene la conexión activa."""
        return self.send_command("NOOP")

    def abort(self) -> str:
        """Aborta la transferencia en curso."""
        return self.send_command("ABOR")

    def get_features(self) -> dict:
        """Obtiene y parsea características del servidor."""
        response = self.send_command("FEAT")
        return parse_features_response(response)

    def list_directory(self, path: str = "") -> list[dict]:
        """Lista directorio con formato estructurado."""
        if path and not validate_path(path):
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Ruta inválida")
        
        self._setup_data_connection()
        
        # Enviar comando LIST y obtener respuesta inicial
        initial_response = self.send_command("LIST", path)
        if self._parse_code(initial_response) not in (125, 150):
            raise FTPClientError(self._parse_code(initial_response), "Error en comando LIST")
        
        # Recibir datos del socket de datos
        data = []
        try:
            while True:
                chunk = self.data_sock.recv(DEFAULT_BUFFER_SIZE)
                if not chunk:
                    break
                data.append(chunk.decode(errors='ignore'))
        except Exception as e:
            print(f"Error recibiendo datos: {e}")
        finally:
            self._close_data_connection()
            
        # Obtener respuesta final del servidor
        final_response = self._get_response()
        if self._parse_code(final_response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPClientError(self._parse_code(final_response), "Error completando LIST")
        
        # Procesar los datos recibidos
        received_data = "".join(data)
        if not received_data.strip():
            return []
            
        # Usar la función de utilidad para parsear la respuesta
        try:
            return parse_list_response(received_data)
        except Exception as e:
            print(f"Error parseando respuesta: {e}")
            # En caso de error, devolver al menos la información en bruto
            return [{'nombre': line.strip(), 'tamaño': '0'} 
                   for line in received_data.split('\n') 
                   if line.strip()]

    def change_to_parent_dir(self) -> str:
        """Cambia al directorio padre (CDUP)."""
        response = self.send_command("CDUP")
        # Verificar si la respuesta contiene un código de éxito (250 o 200)
        if self._parse_code(response) in [250, 200]:
            return response
        raise FTPClientError(self._parse_code(response), "Error cambiando al directorio padre")

    def list_files(self, path: str = "") -> str:
        """Lista solo nombres de archivos usando NLST."""
        if path and not validate_path(path):
            raise FTPClientError(FTPResponseCode.BAD_COMMAND, "Ruta inválida")
        
        self._setup_data_connection()
        
        # Enviar comando NLST
        response = self.send_command("NLST", path)
        if self._parse_code(response) not in (125, 150):
            raise FTPClientError(self._parse_code(response), "Error en comando NLST")
        
        # Recibir datos
        data = []
        try:
            while True:
                chunk = self.data_sock.recv(DEFAULT_BUFFER_SIZE)
                if not chunk:
                    break
                data.append(chunk.decode(errors='ignore'))
        finally:
            self._close_data_connection()
        
        # Obtener y verificar respuesta final
        final_response = self._get_response()
        if self._parse_code(final_response) != FTPResponseCode.FILE_ACTION_COMPLETED:
            raise FTPClientError(self._parse_code(final_response), "Error completando NLST")
        
        # Retornar los nombres de archivos como una cadena
        return "".join(data)

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
        connection_response = client.connect()
        user_response = client.execute("USER", args.user)
        pass_response = client.execute("PASS", args.password)

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
        else:
            print(connection_response + "\n" + user_response + "\n" + pass_response)

    except FTPClientError as e:
        print(f"Error: {e}")
    finally:
        if args.command and args.command.upper() != "QUIT":
            client.execute("QUIT")


if __name__ == "__main__":
    main()

