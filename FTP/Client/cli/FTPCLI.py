import cmd
from FTP.Client.client import FTPClient

class FTPCLI(cmd.Cmd):
    """Command-line interface for the FTP client."""

    prompt = "ftp> "

    def __init__(self, client):
        super().__init__()
        self.client = client

    def do_list(self, arg):
        """Lists files on the server: LIST [path]"""
        try:
            response = self.client.execute("LIST", arg)
            print(response)
        except Exception as e:
            print(f"Error: {e}")

    def do_retr(self, arg):
        """Downloads a file: RETR <remote_path> <local_path>"""
        args = arg.split()
        if len(args) != 2:
            print("Usage: RETR <remote_path> <local_path>")
            return
        try:
            response = self.client.download_file(args[0], args[1])
            print(response)
        except Exception as e:
            print(f"Error: {e}")

    def do_stor(self, arg):
        """Uploads a file: STOR <local_path> <remote_path>"""
        args = arg.split()
        if len(args) != 2:
            print("Usage: STOR <local_path> <remote_path>")
            return
        try:
            response = self.client.upload_file(args[0], args[1])
            print(response)
        except Exception as e:
            print(f"Error: {e}")

    def do_quit(self, arg):
        """Closes the connection: QUIT"""
        try:
            response = self.client.quit()
            print(response)
        except Exception as e:
            print(f"Error: {e}")
        return True

if __name__ == "__main__":
    client = FTPClient('localhost', 21)
    try:
        client.connect()
        client.execute("USER", "username")
        client.execute("PASS", "password")
    except Exception as e:
        print(f"Connection error: {e}")
        exit(1)

    cli = FTPCLI(client)
    cli.cmdloop()