from FTP.Common.exceptions import FTPAuthError
from FTP.Server.Commands.base_command import Command


class SiteCommand(Command):
    def execute(self, server, client_socket, args):
        """Maneja comandos específicos del sitio.

        Comandos soportados:
          ADDUSER    - Agregar un nuevo usuario: SITE ADDUSER <username> <password>
          REMOVEUSER - Eliminar un usuario: SITE REMOVEUSER <username>
          PASSRESET  - Restablecer la contraseña de un usuario: SITE PASSRESET <username> <new_password>
          LISTUSERS  - Listar todos los usuarios
          HELP       - Mostrar la ayuda de los comandos SITE
        """
        if not args:
            return "501 Syntax error in parameters\r\n"

        site_command = args[0].upper()
        site_args = args[1:]

        if site_command == "HELP":
            return (
                "214-The following SITE commands are supported:\r\n"
                "  ADDUSER    - Add a new user (SITE ADDUSER <username> <password>)\r\n"
                "  REMOVEUSER - Remove a user (SITE REMOVEUSER <username>)\r\n"
                "  PASSRESET  - Reset a user's password (SITE PASSRESET <username> <new_password>)\r\n"
                "  LISTUSERS  - List all users\r\n"
                "  HELP       - Show this help\r\n"
                "214 End of help\r\n"
            )

        elif site_command == "ADDUSER":
            if len(site_args) != 2:
                return "501 Syntax error, expected: SITE ADDUSER <username> <password>\r\n"
            username, password = site_args
            try:
                server.credentials_manager.add_user(username, password)
                return f"200 User {username} added successfully\r\n"
            except ValueError as ve:
                return f"550 {ve}\r\n"

        elif site_command == "REMOVEUSER":
            if len(site_args) != 1:
                return "501 Syntax error, expected: SITE REMOVEUSER <username>\r\n"
            username = site_args[0]
            try:
                server.credentials_manager.remove_user(username)
                return f"200 User {username} removed successfully\r\n"
            except ValueError as ve:
                return f"550 {ve}\r\n"

        elif site_command == "PASSRESET":
            if len(site_args) != 3:
                return "501 Syntax error, expected: SITE PASSRESET <username> <old_password> <new_password>\r\n"
            username, old_password ,new_password = site_args
            if not server.credentials_manager.verify_user(username, old_password):
                return FTPAuthError(530, "Authentication failed\r\n")
            try:
                server.credentials_manager.reset_password(username, new_password)
                return f"200 Password for {username} reset successfully\r\n"
            except ValueError as ve:
                return f"550 {ve}\r\n"

        elif site_command == "LISTUSERS":
            users = list(server.credentials_manager.list_users())
            if users:
                return "200 Users: " + ", ".join(users) + "\r\n"
            else:
                return "200 No users found\r\n"

        else:
            return "500 Unknown SITE command\r\n"
