from pathlib import Path
from FTP.Server.Commands.base_command import Command

class RetrCommand(Command):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax error\r\n"

        if not server.create_data_connection():
            return "425 No data connection\r\n"

        try:
            # El servidor solo maneja la ruta remota (en su sistema de archivos)
            file_path = server.current_dir / args[0]
            if file_path.is_file():
                client_socket.send(b"150 Opening data connection for file transfer\r\n")
                
                # Modo de apertura según el tipo de transferencia
                mode = 'r' if server.transfer_type == 'A' else 'rb'
                encoding = 'utf-8' if server.transfer_type == 'A' else None
                
                with open(file_path, mode, encoding=encoding) as f:
                    while True:
                        data = f.read(8192)
                        if not data:
                            break
                        # Para ASCII, asegurar terminaciones de línea correctas
                        if server.transfer_type == 'A':
                            data = data.replace('\n', '\r\n').encode('utf-8')
                        # Para binario, los datos ya están en bytes
                        server.data_socket.send(data if isinstance(data, bytes) else data.encode())
                return "226 Transfer complete\r\n"
            else:
                return "550 File not found\r\n"
        except:
            return "550 Error reading file\r\n"
        finally:
            if server.data_socket:
                server.data_socket.close()
                server.data_socket = None
            if server.passive_server:
                server.passive_server.close()
                server.passive_server = None

class StorCommand(Command):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax error\r\n"

        if not server.create_data_connection():
            return "425 No data connection\r\n"

        try:
            original_path = server.current_dir / args[0]
            file_path = self._get_unique_path(original_path)
            
            client_socket.send(f"150 Opening data connection for file transfer. Saving as {file_path.name}\r\n".encode())
            
            with open(file_path, 'wb') as f:
                while True:
                    data = server.data_socket.recv(8192)
                    if not data:
                        break
                    f.write(data)
            return "226 Transfer complete\r\n"
        except Exception as e:
            print(f"Error en STOR: {e}")  # Para debugging
            return "550 Error storing file\r\n"
        finally:
            if server.data_socket:
                server.data_socket.close()
                server.data_socket = None

    def _get_unique_path(self, original_path):
        """Genera un nombre único para el archivo si ya existe."""
        if not original_path.exists():
            return original_path

        base_name = original_path.stem
        extension = original_path.suffix
        parent_dir = original_path.parent
        counter = 1

        while True:
            new_name = f"{base_name} ({counter}){extension}"
            new_path = parent_dir / new_name
            if not new_path.exists():
                return new_path
            counter += 1

class StouCommand(Command):
    def execute(self, server, client_socket, args):
        import tempfile
        if not server.create_data_connection():
            return "425 No data connection\r\n"
            
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir=server.current_dir)
            temp_name = Path(temp_file.name).name
            client_socket.send(f"150 File will be saved as {temp_name}\r\n".encode())
            
            with open(temp_file.name, 'wb') as f:
                while True:
                    data = server.data_socket.recv(8192)
                    if not data:
                        break
                    f.write(data)
                    
            return f"226 Transfer complete. Saved as {temp_name}\r\n"
        except:
            return "550 Error in STOU\r\n"

class AppeCommand(Command):
    def execute(self, server, client_socket, args):
        """Añade datos a un archivo existente"""
        if not args:
            return "501 Syntax error - se requiere nombre de archivo\r\n"
            
        if not server.create_data_connection():
            return "425 No data connection\r\n"

        try:
            file_path = server.current_dir / args[0]
            # Determinar modo de apertura basado en el tipo de transferencia
            mode = 'a' if server.transfer_type == 'A' else 'ab'
            encoding = 'utf-8' if server.transfer_type == 'A' else None
            client_socket.send(b"150 Opening connection for append\r\n")
            with open(file_path, mode, encoding=encoding) as f:
                while True:
                    data = server.data_socket.recv(8192)
                    if not data:
                        break
                        
                    if server.transfer_type == 'A':
                        # En modo ASCII, decodificar y normalizar finales de línea
                        text = data.decode('utf-8').replace('\r\n', '\n')
                        f.write(text)
                    else:
                        # En modo binario, escribir directamente
                        f.write(data)
                        
            return "226 Transfer complete\r\n"
            
        except Exception as e:
            print(f"Error en APPE: {e}")  # Para debugging
            return "550 Error appending to file\r\n"
        finally:
            if server.data_socket:
                server.data_socket.close()
                server.data_socket = None
