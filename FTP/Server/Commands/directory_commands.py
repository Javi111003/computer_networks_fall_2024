from FTP.Server.Commands.file_system_command import FileSystemCommand

class PwdCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        try:
            # Obtener ruta relativa desde el directorio base
            rel_path = server.current_dir.relative_to(server.base_dir)
            # Si estamos en el directorio base, mostrar "/"
            if str(rel_path) == '.':
                response = f'257 "/"\r\n'
            else:
                response = f'257 "/{rel_path}"\r\n'
            return response
        except Exception as e:
            return f'550 Error getting current directory: {str(e)}\r\n'

class CwdCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax error\r\n"
        try:
            new_path = self.resolve_path(server, args[0])
            if new_path and new_path.exists() and new_path.is_dir():
                server.current_dir = new_path
                return "250 Directory changed successfully\r\n"
            else:
                return "550 Directory does not exist\r\n"
        except:
            return "550 Error changing directory\r\n"

class MkdCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax error\r\n"
        try:
            new_dir = self.resolve_path(server, args[0])
            new_dir.mkdir(parents=True, exist_ok=True)
            return f"257 \"{new_dir}\" created\r\n"
        except:
            return "550 Error creating directory\r\n"

class RmdCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax error\r\n"
        try:
            dir_to_remove = self.resolve_path(server, args[0])
            if dir_to_remove.is_dir():
                dir_to_remove.rmdir()
                return "250 Directory removed\r\n"
            return "550 Not a directory\r\n"
        except:
            return "550 Error removing directory\r\n"

class DeleCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax error\r\n"
        try:
            file_to_delete = self.resolve_path(server, args[0])
            if file_to_delete.is_file():
                file_to_delete.unlink()
                return "250 File deleted\r\n"
            return "550 Not a file\r\n"
        except:
            return "550 Error deleting file\r\n"

class RnfrCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax error\r\n"
        file_path = self.resolve_path(server, args[0])
        if file_path.exists():
            server.rename_from = file_path
            return "350 Ready for RNTO\r\n"
        return "550 File not found\r\n"

class RntoCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        if not server.rename_from or not args:
            return "503 RNFR required first\r\n"
        try:
            new_path = self.resolve_path(server, args[0])
            server.rename_from.rename(new_path)
            server.rename_from = None
            return "250 File renamed successfully\r\n"
        except:
            return "553 Rename failed\r\n"

class ListCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        if not server.create_data_connection():
            return "425 No data connection\r\n"

        try:
            path = self.resolve_path(server, args[0]) if args else server.current_dir
            print(f"Listando directorio: {path}")  # Debug
            
            client_socket.send(b"150 Opening data connection for LIST\r\n")
            
            # Generar listado simplificado
            files_info = []
            for f in path.iterdir():
                # Obtener tamaño y nombre solamente
                size = f.stat().st_size
                file_info = f"{f.name:<50} {size:>10}"
                files_info.append(file_info)
                print(f"Archivo encontrado: {file_info}")  # Debug
            
            listing = "\r\n".join(files_info)
            server.data_socket.send(listing.encode() + b"\r\n")
            return "226 Transfer complete\r\n"
        except Exception as e:
            print(f"Error en LIST: {e}")  # Debug
            return f"550 Error listing directory: {str(e)}\r\n"
        finally:
            if server.data_socket:
                server.data_socket.close()
                server.data_socket = None

class NlstCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        if not server.create_data_connection():
            return "425 No data connection\r\n"

        try:
            path = self.resolve_path(server, args[0]) if args else server.current_dir
            client_socket.send(b"150 Opening data connection for NLST\r\n")
            files = "\r\n".join(str(f.name) for f in path.iterdir() if f.is_file())
            server.data_socket.send(files.encode() + b"\r\n")
            server.data_socket.close()
            return "226 Transfer complete\r\n"
        except:
            return "550 Error listing files\r\n"
        finally:
            if server.data_socket:
                server.data_socket.close()
                server.data_socket = None

class CdupCommand(FileSystemCommand):
    def execute(self, server, client_socket, args):
        try:
            # Obtener el directorio padre
            new_path = server.current_dir.parent
            
            # Verificar que el nuevo path esté dentro del directorio base
            if not new_path.is_relative_to(server.base_dir):
                return "550 No se puede subir más allá del directorio base\r\n"
            
            # Verificar que el directorio existe
            if not new_path.exists():
                return "550 El directorio padre no existe\r\n"
            
            # Actualizar el directorio actual
            server.current_dir = new_path
            return "200 Directorio cambiado al padre exitosamente\r\n"
            
        except Exception as e:
            print(f"Error en CDUP: {e}")  # Para debugging
            return "550 Error cambiando al directorio padre\r\n"
