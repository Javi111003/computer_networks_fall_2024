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

        password = args[0]
        if server.credentials_manager.verify_user(server.current_user, password):
            server.authenticated = True
            client_socket.send(b"230 User logged in\r\n")
        else:
            client_socket.send(b"530 Login incorrect\r\n")