import cmd
from FTP.Client.client import FTPClient
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint
from rich.text import Text
from rich.style import Style

class FTPCLI(cmd.Cmd):
    # Usando Text de rich para el intro para asegurar el color
    intro = None  # Cambiado a None para evitar que cmd.Cmd lo imprima
    _intro_text = Text("""
╔════════════════════════════════════════╗
║             FTP Client v1.0             ║
║      Escriba 'help' para ayuda          ║
╚════════════════════════════════════════╝
    """, style="blue")

    # El prompt necesita ser una cadena plana para cmd.Cmd
    prompt = "ftp> "
    
    def __init__(self, client=None):
        super().__init__()
        self.console = Console()
        self.client = client
        self.connected = client is not None
        # Configurar el estilo del prompt
        self.prompt_style = Style(color="green", bold=True)
        
    def precmd(self, line):
        """Procesa el comando antes de ejecutarlo"""
        # Mostrar el prompt con color usando rich
        self.console.print("ftp> ", style=self.prompt_style, end="")
        return line

    def preloop(self):
        """Se ejecuta antes de iniciar el loop de comandos"""
        # Imprimir el banner de inicio con rich
        self.console.print(self._intro_text)

    def default(self, line):
        """Maneja comandos no reconocidos"""
        self.console.print(f"[red]Error: Comando '{line}' no reconocido. Use 'help' para ver comandos disponibles.[/red]")

    def do_connect(self, arg):
        """Conecta al servidor FTP: connect <host> [port]"""
        args = arg.split()
        if not args:
            self.console.print("[red]Error: Uso: connect <host> [port][/red]")
            return

        host = args[0]
        port = int(args[1]) if len(args) > 1 else 21

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}")
        ) as progress:
            task = progress.add_task(description=f"Conectando a {host}:{port}...", total=None)
            try:
                self.client = FTPClient(host, port)
                self.client.connect()
                self.connected = True
                self.console.print("[green]✓ Conexión establecida[/green]")
            except Exception as e:
                self.console.print(f"[red]✗ Error de conexión: {e}[/red]")

    def do_user(self, arg):
        """Especifica el nombre de usuario: USER <username>"""
        if not arg:
            self.console.print("[red]Error: Uso: USER <username>[/red]")
            return
        try:
            response = self.client.execute("USER", arg)
            self.console.print(f"[cyan]{response}[/cyan]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_pass(self, arg):
        """Especifica la contraseña: PASS <password>"""
        if not arg:
            self.console.print("[red]Error: Uso: PASS <password>[/red]")
            return
        try:
            response = self.client.execute("PASS", arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    # Puedes mantener login como una alternativa conveniente
    def do_login(self, arg):
        """Inicia sesión en el servidor: login <username> <password>"""
        if not self.client:
            self.console.print("[red]Error: No hay conexión. Use 'connect' primero.[/red]")
            return

        args = arg.split()
        if len(args) != 2:
            self.console.print("[red]Error: Uso: login <username> <password>[/red]")
            return

        try:
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
                task = progress.add_task(description="Autenticando...", total=None)
                response = self.client.execute("USER", args[0])
                self.console.print(f"[cyan]{response}[/cyan]")
                response = self.client.execute("PASS", args[1])
                self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]✗ Error de autenticación: {e}[/red]")

    def do_list(self, arg):
        """Lists files on the server: LIST [path]"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}")
        ) as progress:
            task = progress.add_task(description="Obteniendo lista de archivos...", total=None)
            try:
                response = self.client.execute("LIST", arg)
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Permisos")
                table.add_column("Enlaces")
                table.add_column("Propietario")
                table.add_column("Grupo")
                table.add_column("Tamaño")
                table.add_column("Fecha")
                table.add_column("Nombre")

                for line in response.split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 9:
                            table.add_row(*parts[:7], " ".join(parts[8:]))

                self.console.print(table)
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")

    def do_retr(self, arg):
        """Downloads a file: RETR <remote_path> <local_path>"""
        args = arg.split()
        if len(args) != 2:
            self.console.print("[red]Error: Uso: RETR <remote_path> <local_path>[/red]")
            return

        with Progress() as progress:
            task = progress.add_task("[cyan]Descargando...", total=100)
            try:
                response = self.client.download_file(args[0], args[1])
                self.console.print(f"[green]✓ {response}[/green]")
            except Exception as e:
                self.console.print(f"[red]✗ Error: {e}[/red]")

    def do_stor(self, arg):
        """Uploads a file: STOR <local_path> <remote_path>"""
        args = arg.split()
        if len(args) != 2:
            self.console.print("[red]Error: Uso: STOR <local_path> <remote_path>[/red]")
            return

        with Progress() as progress:
            task = progress.add_task("[cyan]Subiendo...", total=100)
            try:
                response = self.client.upload_file(args[0], args[1])
                self.console.print(f"[green]✓ {response}[/green]")
            except Exception as e:
                self.console.print(f"[red]✗ Error: {e}[/red]")

    def do_quit(self, arg):
        """Closes the connection: QUIT"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}")
        ) as progress:
            progress.add_task(description="Cerrando conexión...", total=None)
            try:
                response = self.client.quit()
                self.console.print("[green]✓ Conexión cerrada correctamente[/green]")
            except Exception as e:
                self.console.print(f"[red]✗ Error al cerrar: {e}[/red]")
        return True

    def do_help(self, arg):
        """Muestra la ayuda de los comandos disponibles"""
        commands = {
            "CONEXIÓN": {
                "connect": "Conectar al servidor: connect <host> [port]",
                "login": "Iniciar sesión: login <username> <password>",
                "quit": "Cerrar conexión y salir"
            },
            "NAVEGACIÓN": {
                "pwd": "Mostrar directorio actual",
                "cwd": "Cambiar directorio: cwd <path>",
                "cdup": "Subir al directorio padre",
                "list": "Listar archivos: list [path]"
            },
            "TRANSFERENCIA": {
                "retr": "Descargar archivo: retr <remote_path> <local_path>",
                "stor": "Subir archivo: stor <local_path> <remote_path>",
                "type": "Tipo de transferencia: type <A|E|I>",
                "mode": "Modo de transferencia: mode <S|B|C>",
                "stru": "Estructura de archivo: stru <F|R|P>",
                "rest": "Establecer punto de reinicio: rest <marker>"
            },
            "GESTIÓN": {
                "mkd": "Crear directorio: mkd <path>",
                "rmd": "Eliminar directorio: rmd <path>",
                "dele": "Eliminar archivo: dele <filename>",
                "rnfr": "Renombrar archivo (origen): rnfr <old_name>",
                "rnto": "Renombrar archivo (destino): rnto <new_name>"
            },
            "INFORMACIÓN": {
                "syst": "Información del sistema",
                "stat": "Estado del servidor: stat [<path>]",
                "help": "Mostrar esta ayuda",
                "noop": "Mantener conexión activa",
                "feat": "Listar características del servidor"
            }
        }

        table = Table(show_header=True, header_style="bold magenta", title="Comandos FTP Disponibles", 
                     title_style="bold blue", border_style="blue")
        table.add_column("Categoría", style="cyan")
        table.add_column("Comando", style="green")
        table.add_column("Descripción", style="white")

        for category, cmds in commands.items():
            for cmd, desc in cmds.items():
                table.add_row(category, cmd, desc)

        self.console.print(table)

    def do_type(self, arg):
        """Configura el tipo de transferencia: TYPE <A|E|I> [<N|T|C>]"""
        try:
            args = arg.split()
            response = self.client.set_type(*args)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_mode(self, arg):
        """Configura el modo de transferencia: MODE <S|B|C>"""
        try:
            response = self.client.set_mode(arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_stru(self, arg):
        """Configura la estructura del archivo: STRU <F|R|P>"""
        try:
            response = self.client.set_structure(arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_rest(self, arg):
        """Establece punto de reinicio: REST <marker>"""
        try:
            response = self.client.set_restart_point(arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_pwd(self, arg):
        """Muestra el directorio actual"""
        try:
            response = self.client.get_current_dir()
            self.console.print(f"[cyan]Directorio actual: {response}[/cyan]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_cwd(self, arg):
        """Cambia el directorio de trabajo: CWD <path>"""
        try:
            response = self.client.change_dir(arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_cdup(self, arg):
        """Cambia al directorio padre"""
        try:
            response = self.client.change_to_parent_dir()
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_mkd(self, arg):
        """Crea un directorio: MKD <path>"""
        try:
            response = self.client.make_dir(arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_rmd(self, arg):
        """Elimina un directorio: RMD <path>"""
        try:
            response = self.client.remove_dir(arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_dele(self, arg):
        """Elimina un archivo: DELE <filename>"""
        try:
            response = self.client.delete_file(arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_rnfr(self, arg):
        """Especifica el archivo a renombrar: RNFR <old_name>"""
        try:
            response = self.client.rename_from(arg)
            self.console.print(f"[cyan]Archivo seleccionado para renombrar[/cyan]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_rnto(self, arg):
        """Especifica el nuevo nombre: RNTO <new_name>"""
        try:
            response = self.client.rename_to(arg)
            self.console.print(f"[green]✓ Archivo renombrado exitosamente[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_syst(self, arg):
        """Muestra información del sistema"""
        try:
            response = self.client.get_system()
            self.console.print(f"[cyan]{response}[/cyan]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_stat(self, arg):
        """Muestra el estado del servidor o archivo: STAT [<path>]"""
        try:
            response = self.client.get_status(arg)
            self.console.print(f"[cyan]{response}[/cyan]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_noop(self, arg):
        """Mantiene la conexión activa: NOOP"""
        try:
            response = self.client.noop()
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_feat(self, arg):
        """Muestra las características del servidor"""
        try:
            features = self.client.get_features()
            self.console.print("[cyan]Características del servidor:[/cyan]")
            for feature, details in features.items():
                self.console.print(f"[green]- {feature}[/green]: {details}")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def emptyline(self):
        """No hacer nada cuando se presiona Enter sin comando"""
        pass

if __name__ == "__main__":
    try:
        client = FTPClient('localhost', 21)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}")
        ) as progress:
            progress.add_task(description="Conectando al servidor...", total=None)
            try:
                client.connect()
                client.execute("USER", "username")
                client.execute("PASS", "password")
                rprint("[green]✓ Conexión establecida[/green]")
            except Exception as e:
                rprint(f"[red]Connection error: {e}[/red]")
                exit(1)

        cli = FTPCLI(client)
        cli.cmdloop()
    except KeyboardInterrupt:
        rprint("\n[yellow]¡Hasta luego![/yellow]")