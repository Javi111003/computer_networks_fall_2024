from FTP.Server.Commands.base_command import Command

class UserCommand(Command):
    def execute(self, server, client_socket, args):
        if not args:
            client_socket.send(b"501 Syntax error\r\n")
            return

        server.current_user = args[0]
        client_socket.send(b"331 User name okay, need password\r\n")

class PassCommand(Command):
    def execute(self, server, client_socket, args):
        if not server.current_user:
            client_socket.send(b"503 Login with USER first\r\n")
            return

        # Aquí iría la lógica real de autenticación
        client_socket.send(b"230 User logged in\r\n")