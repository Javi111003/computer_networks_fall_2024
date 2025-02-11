import socket
import os
from pathlib import Path
from typing import Dict, Optional
from FTP.Server.Commands.auth import UserCommand, PassCommand
from FTP.Server.Commands.transfer_commands import RetrCommand, StorCommand, StouCommand, AppeCommand
from FTP.Server.Commands.directory_commands import (PwdCommand, CwdCommand, MkdCommand,
                                                RmdCommand, DeleCommand, RnfrCommand,
                                                RntoCommand, ListCommand, CdupCommand,
                                                NlstCommand)
from FTP.Server.Commands.system_commands import (SystCommand, StatCommand, NoopCommand,
                                             HelpCommand, QuitCommand, TypeCommand,
                                             ModeCommand, StruCommand, FeatCommand,
                                             RestCommand,
                                             ReinCommand, AbortCommand, OptsCommand, SiteCommand)
from FTP.Server.Commands.connection_commands import PasvCommand, PortCommand
from FTP.Server.Commands.base_command import Command

class FTPServer:
    def __init__(self, host='0.0.0.0', port=21, base_dir=None):
        self.host = host
        self.port = port
        # Usar el directorio especificado o crear uno por defecto
        if base_dir is None:
            self.base_dir = Path(__file__).parent.parent / 'FTPRoot'
        else:
            self.base_dir = Path(base_dir)

        print(f"Directorio base del servidor: {self.base_dir}")  # Debug
        # Crear el directorio si no existe
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_dir = self.base_dir
        self.current_user: Optional[str] = None
        self.commands: Dict[str, Command] = {}
        self._register_commands()

        # Estado de la conexión de datos
        self.data_socket: Optional[socket.socket] = None
        self.passive_server: Optional[socket.socket] = None
        self.passive_mode = False
        self.data_addr: Optional[str] = None
        self.data_port: Optional[int] = None

        # Estado de la transferencia
        self.transfer_type = 'A'  # ASCII por defecto
        self.structure = 'F'      # File por defecto
        self.mode = 'S'          # Stream por defecto
        self.rename_from: Optional[Path] = None

    def _register_commands(self) -> None:
        """Registra todos los comandos disponibles"""
        commands = {
            # Comandos de autenticación
            "USER": UserCommand(),
            "PASS": PassCommand(),

            # Comandos de directorio
            "PWD": PwdCommand(),
            "CWD": CwdCommand(),
            "MKD": MkdCommand(),
            "RMD": RmdCommand(),
            "DELE": DeleCommand(),
            "RNFR": RnfrCommand(),
            "RNTO": RntoCommand(),
            "LIST": ListCommand(),
            "CDUP": CdupCommand(),
            "NLST": NlstCommand(),

            # Comandos de transferencia
            "RETR": RetrCommand(),
            "STOR": StorCommand(),
            "STOU": StouCommand(),
            "APPE": AppeCommand(),

            # Comandos de conexión
            "PASV": PasvCommand(),
            "PORT": PortCommand(),

            # Comandos de sistema
            "SYST": SystCommand(),
            "STAT": StatCommand(),
            "NOOP": NoopCommand(),
            "HELP": HelpCommand(),
            "QUIT": QuitCommand(),
            "TYPE": TypeCommand(),
            "MODE": ModeCommand(),
            "STRU": StruCommand(),
            "FEAT": FeatCommand(),
            "REST": RestCommand(),
            "REIN": ReinCommand(),
            "ABOR": AbortCommand(),
            "OPTS": OptsCommand(),
            "SITE": SiteCommand(),
        }
        self.commands.update(commands)

    def start(self) -> None:
        """Inicia el servidor FTP"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Servidor FTP iniciado en {self.host}:{self.port}")

        while True:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"Cliente conectado: {client_address}")
                self.handle_client(client_socket)
            except Exception as e:
                print(f"Error en conexión: {e}")

    def handle_client(self, client_socket: socket.socket) -> None:
        """Maneja la conexión con un cliente"""
        try:
            client_socket.send(b"220 Bienvenido al servidor FTP\r\n")

            while True:
                try:
                    data = client_socket.recv(1024).decode().strip()
                    if not data:
                        break

                    print(f"Comando recibido: {data}")
                    cmd_parts = data.split()
                    cmd = cmd_parts[0].upper()
                    args = cmd_parts[1:] if len(cmd_parts) > 1 else []

                    if cmd in self.commands:
                        command = self.commands[cmd]
                        response = command.execute(self, client_socket, args)
                        if response:
                            client_socket.send(response.encode())

                        if cmd == "QUIT":
                            break
                    else:
                        client_socket.send(b"502 Comando no implementado\r\n")

                except Exception as e:
                    print(f"Error procesando comando: {e}")
                    client_socket.send(b"500 Error interno del servidor\r\n")

        except Exception as e:
            print(f"Error en sesión de cliente: {e}")
        finally:
            self._cleanup_client(client_socket)

    def _cleanup_client(self, client_socket: socket.socket) -> None:
        """Limpia recursos asociados a un cliente"""
        try:
            client_socket.close()
        except:
            pass

        self._cleanup_data_connection()
        self.current_user = None
        self.current_dir = self.base_dir
        self.rename_from = None

    def _cleanup_data_connection(self) -> None:
        """Limpia la conexión de datos"""
        if self.data_socket:
            try:
                self.data_socket.close()
            except:
                pass
            self.data_socket = None

        if self.passive_server:
            try:
                self.passive_server.close()
            except:
                pass
            self.passive_server = None

        self.passive_mode = False
        self.data_addr = None
        self.data_port = None

    def create_data_connection(self) -> bool:
        """Establece la conexión de datos según el modo actual"""
        try:
            if self.passive_mode and self.passive_server:
                self.data_socket, _ = self.passive_server.accept()
                return True
            elif not self.passive_mode and self.data_addr and self.data_port:
                self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.data_socket.connect((self.data_addr, self.data_port))
                return True
            return False
        except Exception as e:
            print(f"Error en conexión de datos: {e}")
            return False

if __name__ == "__main__":
    # Directorio base por defecto en la carpeta FTPRoot
    default_base_dir = Path(__file__).parent.parent / 'FTPRoot'
    server = FTPServer(base_dir=default_base_dir)
    server.start()