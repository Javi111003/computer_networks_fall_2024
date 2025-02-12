from FTP.Server.Commands.base_command import Command

class FeatCommand(Command):
    def execute(self, server, client_socket, args):
        features = """211-Features:
 PASV
 SIZE
 UTF8
 REST STREAM
211 End"""
        return features + "\r\n"

class RestCommand(Command):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax error\r\n"
        try:
            server.restart_point = int(args[0])
            return "350 Restarting at position\r\n"
        except ValueError:
            return "501 Invalid restart point\r\n"

class ReinCommand(Command):
    def execute(self, server, client_socket, args):
        """Reinicializa la conexión"""
        server.current_user = None
        server.authenticated = False
        server.current_dir = server.base_dir
        return "220 Service ready for new user\r\n"

class AbortCommand(Command):
    def execute(self, server, client_socket, args):
        """Aborta la operación actual"""
        if server.data_socket:
            server.data_socket.close()
            server.data_socket = None
        if server.passive_server:
            server.passive_server.close()
            server.passive_server = None
        return "226 ABOR command successful\r\n"

class SystCommand(Command):
    def execute(self, server, client_socket, args):
        return "215 UNIX Type: L8\r\n"

class StatCommand(Command):
    def execute(self, server, client_socket, args):
        """Muestra información detallada del estado del servidor"""
        try:
            response = "211-Server status:\r\n"
            # Información de conexión
            response += f"    Connected from: {client_socket.getpeername()[0]}:{client_socket.getpeername()[1]}\r\n"
            response += f"    Server address: {server.host}:{server.port}\r\n"
            response += f"    Current user: {server.current_user}\r\n"

            # Información del sistema de archivos
            response += f"    Current directory: {server.current_dir}\r\n"
            response += f"    Base directory: {server.base_dir}\r\n"

            # Información de transferencia
            response += f"    Transfer type: {server.transfer_type}\r\n"
            response += f"    Structure: {server.structure}\r\n"
            response += f"    Mode: {server.mode}\r\n"
            response += f"    Passive mode: {'Yes' if server.passive_mode else 'No'}\r\n"
            return response

        except ImportError:
            # Versión simplificada si psutil no está disponible
            response = "211-Server status:\r\n"
            response += f"    Connected from: {client_socket.getpeername()[0]}:{client_socket.getpeername()[1]}\r\n"
            response += f"    Server address: {server.host}:{server.port}\r\n"
            response += f"    Current user: {server.current_user}\r\n"
            response += f"    Current directory: {server.current_dir}\r\n"
            response += f"    Transfer type: {server.transfer_type}\r\n"
            response += "211 End of status\r\n"
            return response
        except Exception as e:
            return f"500 Error getting server status: {str(e)}\r\n"

class NoopCommand(Command):
    def execute(self, server, client_socket, args):
        return "200 NOOP ok\r\n"

class HelpCommand(Command):
    def execute(self, server, client_socket, args):
        commands = ", ".join(sorted(server.commands.keys()))
        return f"214-Available commands:\r\n{commands}\r\n214 End of help.\r\n"

class QuitCommand(Command):
    def execute(self, server, client_socket, args):
        return "221 Goodbye\r\n"

class TypeCommand(Command):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax: TYPE {A,E,I}\r\n"
        type_code = args[0].upper()
        if type_code in ['A', 'E', 'I']:
            server.transfer_type = type_code
            return f"200 Type set to {type_code}\r\n"
        return "504 Type not supported\r\n"

class ModeCommand(Command):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax: MODE {S,B,C}\r\n"
        mode = args[0].upper()
        if mode == 'S':
            server.mode = mode
            return "200 Mode set to Stream\r\n"
        return "504 Mode not supported\r\n"

class StruCommand(Command):
    def execute(self, server, client_socket, args):
        if not args:
            return "501 Syntax: STRU {F,R,P}\r\n"
        structure = args[0].upper()
        if structure == 'F':
            server.structure = structure
            return "200 Structure set to File\r\n"
        return "504 Structure not supported\r\n"

class SiteCommand(Command):
    def execute(self, server, client_socket, args):
        """Maneja comandos específicos del sitio"""
        if not args:
            return "501 Syntax error in parameters\r\n"
        
        site_command = args[0].upper()
        site_args = args[1:]
        
        # Implementar comandos SITE específicos
        if site_command == "CHMOD":
            if len(site_args) >= 2:
                # Aquí iría la lógica para cambiar permisos
                return "200 CHMOD command successful\r\n"
            return "501 Invalid CHMOD parameters\r\n"
            
        elif site_command == "HELP":
            return """214-The following SITE commands are supported:
            CHMOD - Change file permissions
            HELP  - Show this help
            214 End of help\r\n"""
            
        return "500 Unknown SITE command\r\n"
