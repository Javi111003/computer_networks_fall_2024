from pathlib import Path
from abc import ABC, abstractmethod
from FTP.Server.Commands.base_command import Command

class FileSystemCommand(Command):
    def resolve_path(self, server, path):
        """Resuelve una ruta relativa al directorio actual del servidor"""
        try:
            absolute_path = (server.current_dir / path).resolve()

            # Verificar que el path esté dentro del directorio base
            if not absolute_path.is_relative_to(server.base_dir):
                raise ValueError("Path fuera del directorio base")
            return absolute_path
        except:
            return None
    @abstractmethod
    def execute(self, server, client_socket, args):
        pass