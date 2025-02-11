import socket
from pathlib import Path
import shutil
import random
from FTP.Server.Commands.auth import UserCommand, PassCommand

class FTPServer:
    def __init__(self, host='0.0.0.0', port=21):
        self.host = host
        self.port = port
        self.current_user = None
        self.base_dir = Path.cwd()
        self.current_dir = self.base_dir
        self.commands = {}
        self._register_commands()
        self.data_port = 20
        self.transfer_type = 'A'  # ASCII por defecto
        self.structure = 'F'      # File por defecto
        self.mode = 'S'          # Stream por defecto
        self.data_socket = None
        self.passive_server = None
        self.passive_mode = False
        self.data_addr = None
        self.data_port = None

    def _register_commands(self):
        # Registro de comandos con sus funciones correspondientes
        self.add_command("USER", UserCommand()) # guía del patrón command
        self.add_command("PASS", PassCommand()) # APLICAR AL RESTO DE COMANDOS
        self.add_command("PWD", self.handle_pwd)
        self.add_command("CWD", self.handle_cwd)
        self.add_command("LIST", self.handle_list)
        self.add_command("QUIT", self.handle_quit)
        self.add_command("MKD", self.handle_mkd)
        self.add_command("RMD", self.handle_rmd)
        self.add_command("DELE", self.handle_dele)
        self.add_command("RNFR", self.handle_rnfr)
        self.add_command("RNTO", self.handle_rnto)
        self.add_command("SYST", self.handle_syst)
        self.add_command("HELP", self.handle_help)
        self.add_command("NOOP", self.handle_noop)
        self.add_command("ACCT", self.handle_acct)
        self.add_command("SMNT", self.handle_smnt)
        self.add_command("REIN", self.handle_rein)
        self.add_command("PORT", self.handle_port)
        self.add_command("PASV", self.handle_pasv)
        self.add_command("TYPE", self.handle_type)
        self.add_command("STRU", self.handle_stru)
        self.add_command("MODE", self.handle_mode)
        self.add_command("RETR", self.handle_retr)
        self.add_command("STOR", self.handle_stor)
        self.add_command("STOU", self.handle_stou)
        self.add_command("APPE", self.handle_appe)
        self.add_command("ALLO", self.handle_allo)
        self.add_command("REST", self.handle_rest)
        self.add_command("ABOR", self.handle_abor)
        self.add_command("SITE", self.handle_site)
        self.add_command("STAT", self.handle_stat)
        self.add_command("NLST", self.handle_nlst)
        self.add_command("CDUP", self.handle_cdup)

    def add_command(self, cmd_name, cmd_func):
        """Añade un nuevo comando al servidor"""
        self.commands[cmd_name] = cmd_func

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Servidor FTP iniciado en {self.host}:{self.port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Cliente conectado: {client_address}")
            self.handle_client(client_socket)

    def handle_client(self, client_socket):
        client_socket.send(b"220 Bienvenido al servidor FTP\r\n")
        self.rename_from = None  # Para el comando RNFR/RNTO
        
        while True:
            try:
                data = client_socket.recv(1024).decode().strip()
                if not data:
                    break

                print(f"Comando recibido: {data}")
                cmd_parts = data.split()
                cmd = cmd_parts[0].upper()
                args = cmd_parts[1:] if len(cmd_parts) > 1 else []

                if cmd in self.commands:   # Guía del patrón command
                    command = self.commands[cmd]
                    response = command.execute(self, client_socket, args)
                    if response:
                        client_socket.send(response.encode())
                else:
                    client_socket.send(b"502 Comando no implementado\r\n")

            except Exception as e:
                print(f"Error: {e}")
                break

        client_socket.close()

    # ----------------#
    # Manejadores de comandos #
    # ----------------#

    # LLEVAR A CLASES CADA COMANDO , CON SU IMPLEMENTACIÓN DE EXECUTE (ENCAPSULAMIENTO DE ESTOS HANDLERS)
    def handle_user(self, client_socket, args):
        self.current_user = args[0] if args else None
        client_socket.send(b"331 Usuario OK, esperando contrasena\r\n")

    def handle_pass(self, client_socket, args):
        if self.current_user:
            client_socket.send(b"230 Usuario logueado exitosamente\r\n")
        else:
            client_socket.send(b"503 Primero ingrese el usuario\r\n")

    def handle_pwd(self, client_socket, args):
        response = f"257 \"{self.current_dir.relative_to(self.base_dir)}\"\r\n"
        client_socket.send(response.encode())

    def handle_cwd(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            new_path = (self.current_dir / args[0]).resolve()
            if new_path.exists() and new_path.is_dir():
                self.current_dir = new_path
                client_socket.send(b"250 Directorio cambiado exitosamente\r\n")
            else:
                client_socket.send(b"550 Directorio no existe\r\n")
        except:
            client_socket.send(b"550 Error al cambiar directorio\r\n")

    def create_data_connection(self):
        """Establece la conexión de datos según el modo actual"""
        if self.passive_mode:
            if self.passive_server:
                self.data_socket, addr = self.passive_server.accept()
                return True
        else:
            if self.data_addr and self.data_port:
                self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.data_socket.connect((self.data_addr, self.data_port))
                    return True
                except:
                    return False
        return False

    def handle_list(self, client_socket, args):
        """LIST requiere conexión de datos"""
        if not self.create_data_connection():
            client_socket.send(b"425 No data connection\r\n")
            return

        try:
            client_socket.send(b"150 Opening data connection for LIST\r\n")
            files = "\r\n".join(str(f.name) for f in self.current_dir.iterdir())
            self.data_socket.send(files.encode() + b"\r\n")
            self.data_socket.close()
            client_socket.send(b"226 Transfer complete\r\n")
        except:
            client_socket.send(b"550 Error listing files\r\n")
        finally:
            if self.data_socket:
                self.data_socket.close()
                self.data_socket = None
            if self.passive_server:
                self.passive_server.close()
                self.passive_server = None

    def handle_mkd(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            new_dir = (self.current_dir / args[0])
            new_dir.mkdir(parents=True, exist_ok=True)
            client_socket.send(f"257 \"{new_dir}\" creado\r\n".encode())
        except:
            client_socket.send(b"550 Error al crear directorio\r\n")

    def handle_rmd(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            dir_to_remove = (self.current_dir / args[0])
            if dir_to_remove.is_dir():
                shutil.rmtree(dir_to_remove)
                client_socket.send(b"250 Directorio eliminado\r\n")
            else:
                client_socket.send(b"550 No es un directorio\r\n")
        except:
            client_socket.send(b"550 Error al eliminar directorio\r\n")

    def handle_dele(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        try:
            file_to_delete = (self.current_dir / args[0])
            if file_to_delete.is_file():
                file_to_delete.unlink()
                client_socket.send(b"250 Archivo eliminado\r\n")
            else:
                client_socket.send(b"550 No es un archivo\r\n")
        except:
            client_socket.send(b"550 Error al eliminar archivo\r\n")

    def handle_rnfr(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis invalida\r\n")
            return
        file_path = (self.current_dir / args[0])
        if file_path.exists():
            self.rename_from = file_path
            client_socket.send(b"350 Listo para RNTO\r\n")
        else:
            client_socket.send(b"550 Archivo no existe\r\n")

    def handle_rnto(self, client_socket, args):
        if not self.rename_from or not args:
            client_socket.send(b"503 Comando RNFR requerido primero\r\n")
            return
        try:
            new_path = (self.current_dir / args[0])
            self.rename_from.rename(new_path)
            client_socket.send(b"250 Archivo renombrado exitosamente\r\n")
        except:
            client_socket.send(b"553 Error al renombrar\r\n")
        finally:
            self.rename_from = None

    def handle_syst(self, client_socket, args):
        client_socket.send(b"215 UNIX Type: L8\r\n")

    def handle_help(self, client_socket, args):
        commands = ", ".join(sorted(self.commands.keys()))
        response = f"214-Los siguientes comandos están disponibles:\r\n{commands}\r\n214 Fin de ayuda.\r\n"
        client_socket.send(response.encode())

    def handle_noop(self, client_socket, args):
        client_socket.send(b"200 OK\r\n")

    def handle_quit(self, client_socket, args):
        client_socket.send(b"221 Goodbye\r\n")
        return True

    # Nuevos manejadores de comandos
    def handle_acct(self, client_socket, args):
        client_socket.send(b"230 No se requiere cuenta para este servidor\r\n")

    def handle_smnt(self, client_socket, args):
        client_socket.send(b"502 SMNT no implementado\r\n")

    def handle_rein(self, client_socket, args):
        self.current_user = None
        self.current_dir = self.base_dir
        client_socket.send(b"220 Servicio reiniciado\r\n")

    def handle_port(self, client_socket, args):
        """Maneja el comando PORT para modo activo"""
        if not args:
            client_socket.send(b"501 Syntax error\r\n")
            return
        
        # Formato PORT h1,h2,h3,h4,p1,p2
        try:
            nums = args[0].split(',')
            if len(nums) != 6:
                raise ValueError
            
            # Reconstruir dirección IP y puerto
            self.data_addr = '.'.join(nums[:4])
            self.data_port = (int(nums[4]) << 8) + int(nums[5])
            self.passive_mode = False
            
            client_socket.send(b"200 PORT command successful\r\n")
        except:
            client_socket.send(b"501 Invalid PORT command\r\n")

    def handle_pasv(self, client_socket, args):
        """Maneja el comando PASV para modo pasivo"""
        try:
            self.passive_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Elegir puerto aleatorio entre 1024-65535
            passive_port = random.randint(1024, 65535)
            self.passive_server.bind((self.host, passive_port))
            self.passive_server.listen(1)
            
            # Obtener IP local
            host_parts = socket.gethostbyname(socket.gethostname()).split('.')
            port_high = passive_port >> 8
            port_low = passive_port & 0xFF
            
            response = f"227 Entering Passive Mode ({','.join(host_parts)},{port_high},{port_low})\r\n"
            client_socket.send(response.encode())
            self.passive_mode = True
        except:
            client_socket.send(b"425 Can't enter passive mode\r\n")

    def handle_type(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis: TYPE {A,E,I,L}\r\n")
            return
        type_code = args[0].upper()
        if type_code in ['A', 'E', 'I', 'L']:
            client_socket.send(f"200 Tipo establecido a {type_code}\r\n".encode())
        else:
            client_socket.send(b"504 Tipo no soportado\r\n")

    def handle_stru(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis: STRU {F,R,P}\r\n")
            return
        stru_code = args[0].upper()
        if stru_code == 'F':
            client_socket.send(b"200 Estructura establecida a File\r\n")
        else:
            client_socket.send(b"504 Estructura no soportada\r\n")

    def handle_mode(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis: MODE {S,B,C}\r\n")
            return
        mode_code = args[0].upper()
        if mode_code == 'S':
            client_socket.send(b"200 Modo establecido a Stream\r\n")
        else:
            client_socket.send(b"504 Modo no soportado\r\n")

    def handle_retr(self, client_socket, args):
        """RETR requiere conexión de datos"""
        if not args:
            client_socket.send(b"501 Syntax error\r\n")
            return

        if not self.create_data_connection():
            client_socket.send(b"425 No data connection\r\n")
            return

        try:
            file_path = self.current_dir / args[0]
            if file_path.is_file():
                client_socket.send(b"150 Opening data connection for file transfer\r\n")
                with open(file_path, 'rb') as f:
                    while True:
                        data = f.read(8192)
                        if not data:
                            break
                        self.data_socket.send(data)
                client_socket.send(b"226 Transfer complete\r\n")
            else:
                client_socket.send(b"550 File not found\r\n")
        except:
            client_socket.send(b"550 Error reading file\r\n")
        finally:
            if self.data_socket:
                self.data_socket.close()
                self.data_socket = None
            if self.passive_server:
                self.passive_server.close()
                self.passive_server = None

    def handle_stor(self, client_socket, args):
        """STOR requiere conexión de datos"""
        if not args:
            client_socket.send(b"501 Syntax error\r\n")
            return

        if not self.create_data_connection():
            client_socket.send(b"425 No data connection\r\n")
            return

        try:
            file_path = self.current_dir / args[0]
            client_socket.send(b"150 Opening data connection for file transfer\r\n")
            with open(file_path, 'wb') as f:
                while True:
                    data = self.data_socket.recv(8192)
                    if not data:
                        break
                    f.write(data)
            client_socket.send(b"226 Transfer complete\r\n")
        except:
            client_socket.send(b"550 Error storing file\r\n")
        finally:
            if self.data_socket:
                self.data_socket.close()
                self.data_socket = None
            if self.passive_server:
                self.passive_server.close()
                self.passive_server = None

    def handle_stou(self, client_socket, args):
        try:
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir=self.current_dir)
            temp_name = Path(temp_file.name).name
            client_socket.send(f"150 Archivo será almacenado como {temp_name}\r\n".encode())
            
            # Recibir datos
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                temp_file.write(data)
            
            temp_file.close()
            client_socket.send(f"226 Transferencia completa. Archivo guardado como {temp_name}\r\n".encode())
        except:
            client_socket.send(b"550 Error al almacenar archivo\r\n")

    def handle_appe(self, client_socket, args):
        if not args:
            client_socket.send(b"501 Sintaxis: APPE filename\r\n")
            return
        try:
            file_path = self.current_dir / args[0]
            mode = 'ab' if file_path.exists() else 'wb'
            
            client_socket.send(b"150 Listo para recibir datos\r\n")
            with open(file_path, mode) as f:
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    f.write(data)
            
            client_socket.send(b"226 Transferencia completa\r\n")
        except:
            client_socket.send(b"550 Error al anexar al archivo\r\n")

    def handle_allo(self, client_socket, args):
        client_socket.send(b"200 ALLO no necesario\r\n")

    def handle_rest(self, client_socket, args):
        client_socket.send(b"502 REST no implementado\r\n")

    def handle_abor(self, client_socket, args):
        client_socket.send(b"226 ABOR procesado\r\n")

    def handle_site(self, client_socket, args):
        client_socket.send(b"200 Comando SITE no soportado\r\n")

    def handle_stat(self, client_socket, args):
        response = "211-Estado del servidor FTP\r\n"
        response += f"    Usuario: {self.current_user}\r\n"
        response += f"    Directorio actual: {self.current_dir}\r\n"
        response += "211 Fin del estado\r\n"
        client_socket.send(response.encode())

    def handle_nlst(self, client_socket, args):
        try:
            files = "\r\n".join(str(f.name) for f in self.current_dir.iterdir() if f.is_file())
            response = f"150 Lista de archivos:\r\n{files}\r\n226 Transferencia completa\r\n"
            client_socket.send(response.encode())
        except:
            client_socket.send(b"550 Error al listar archivos\r\n")

    def handle_cdup(self, client_socket, args):
        try:
            new_path = self.current_dir.parent
            if new_path.exists():
                self.current_dir = new_path
                client_socket.send(b"200 Directorio cambiado al padre\r\n")
            else:
                client_socket.send(b"550 No se puede subir mas\r\n")
        except:
            client_socket.send(b"550 Error al cambiar directorio\r\n")

if __name__ == "__main__":
    server = FTPServer()
    server.start()