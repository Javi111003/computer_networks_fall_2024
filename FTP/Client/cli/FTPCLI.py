import cmd
from FTP.Client.client import FTPClient
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint
from rich.text import Text
from rich.style import Style
import re

class FTPCLI(cmd.Cmd):
    # Usando Text de rich para el intro para asegurar el color
    intro = None  # Cambiado a None para evitar que cmd.Cmd lo imprima
    _intro_text = Text("""
╔════════════════════════════════════════╗
║             FTP Client v1.0            ║
║      Escriba 'help' para ayuda         ║ 
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
        """Lista archivos en el servidor: LIST [path]"""
        try:
            # Primero entrar en modo pasivo
            self.client.enter_passive_mode()
            
            # Obtener y procesar la lista de archivos
            file_list = self.client.list_directory(arg)
            
            if not file_list:
                self.console.print("[yellow]Directorio vacío o error listando archivos[/yellow]")
                return
            
            # Imprimir encabezado
            self.console.print("\n[bold magenta]Contenido del Directorio:[/bold magenta]")
            self.console.print("[cyan]" + "-" * 50 + "[/cyan]")
            
            # Contador de archivos válidos
            total_files = 0
            
            # Mostrar cada archivo
            for file_info in file_list:
                nombre = file_info.get('nombre', '').strip()
                tamaño = file_info.get('tamaño', '').strip()
                
                # Si el nombre contiene el tamaño (debido al formato del servidor)
                if nombre and nombre.count(' ') > 0:
                    partes = nombre.rsplit(None, 1)
                    if len(partes) == 2:
                        nombre, tam = partes
                        if tam.isdigit():
                            tamaño = tam
                
                # Mostrar solo si el nombre es válido
                if nombre and nombre != "0":
                    total_files += 1
                    
                    # Convertir tamaño a formato legible
                    try:
                        tamaño_num = int(tamaño)
                        if tamaño_num >= 1024*1024*1024:
                            tamaño_fmt = f"{tamaño_num/(1024*1024*1024):.1f} GB"
                        elif tamaño_num >= 1024*1024:
                            tamaño_fmt = f"{tamaño_num/(1024*1024):.1f} MB"
                        elif tamaño_num >= 1024:
                            tamaño_fmt = f"{tamaño_num/1024:.1f} KB"
                        else:
                            tamaño_fmt = f"{tamaño_num} B"
                    except (ValueError, TypeError):
                        tamaño_fmt = tamaño if tamaño else "???"
                    
                    # Mostrar archivo con formato
                    self.console.print(f"[cyan]{nombre:<40}[/cyan] [green]{tamaño_fmt:>10}[/green]")
            
            # Mostrar línea final y total
            self.console.print("[cyan]" + "-" * 50 + "[/cyan]")
            self.console.print(f"[blue]Total: {total_files} elementos[/blue]\n")
            
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")

    def do_retr(self, arg):
        """Downloads a file: RETR <remote_path> <local_path>"""
        args = arg.split()
        if len(args) != 2:
            self.console.print("[red]Error: Uso: RETR <remote_path> <local_path>[/red]")
            self.console.print("[yellow]Ejemplo: retr archivo.txt descarga.txt[/yellow]")
            return

        remote_path, local_path = args
        try:
            # Solo mostramos una barra de progreso y la respuesta final
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("[cyan]Descargando archivo...", total=None)
                response = self.client.download_file(remote_path, local_path)
                
            if "226" in response:  # Transferencia exitosa
                self.console.print(f"[green]✓ Archivo descargado exitosamente como '{local_path}'[/green]")
            else:
                self.console.print(f"[yellow]{response}[/yellow]")

        except Exception as e:
            self.console.print(f"[red]✗ Error: {str(e)}[/red]")
            self.console.print("[yellow]Tip: Verifique que el archivo existe y tiene permisos[/yellow]")

    def do_stor(self, arg):
        """Uploads a file: STOR <local_path> <remote_path>"""
        args = arg.split()
        if len(args) != 2:
            self.console.print("[red]Error: Uso: STOR <local_path> <remote_path>[/red]")
            return

        try:
            # Verificar que el archivo existe antes de intentar subirlo
            from pathlib import Path
            if not Path(args[0]).exists():
                self.console.print(f"[red]Error: El archivo local '{args[0]}' no existe[/red]")
                return

            # Solo mostramos una barra de progreso y la respuesta final
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True  # Esto hace que la barra desaparezca al completar
            ) as progress:
                task = progress.add_task("[cyan]Subiendo archivo...", total=None)
                response = self.client.upload_file(args[0], args[1])
                
            # Mostrar solo el mensaje de éxito
            if "226" in response:  # Si la transferencia fue exitosa
                self.console.print("[green]✓ Archivo subido exitosamente[/green]")
            else:
                self.console.print(f"[yellow]{response}[/yellow]")
                
        except Exception as e:
            self.console.print(f"[red]✗ Error: {e}[/red]")

    def do_appe(self, arg):
        """Añade datos a un archivo: APPE <local_path> <remote_path>"""
        args = arg.split()
        if len(args) != 2:
            self.console.print("[red]Error: Uso: APPE <local_path> <remote_path>[/red]")
            self.console.print("[yellow]Ejemplo: appe local.txt remoto.txt[/yellow]")
            return

        local_path, remote_path = args
        try:
            # Verificar archivo local
            from pathlib import Path
            if not Path(local_path).exists():
                self.console.print(f"[red]Error: El archivo local '{local_path}' no existe[/red]")
                return

            # Mostrar progreso de la operación
            self.console.print("[cyan]Iniciando operación de append...[/cyan]")
            
            try:
                response = self.client.append_file(local_path, remote_path)
                
                # Verificar si la operación fue exitosa
                if "226" in response:  # Código de éxito
                    self.console.print(f"[green]✓ Datos añadidos exitosamente a '{remote_path}'[/green]")
                else:
                    self.console.print(f"[yellow]{response}[/yellow]")

            except Exception as e:
                if "timeout" in str(e).lower():
                    self.console.print("[red]✗ Error: Timeout en la operación[/red]")
                    self.console.print("[yellow]La operación se completó parcialmente[/yellow]")
                else:
                    self.console.print(f"[red]✗ Error: {str(e)}[/red]")

        except Exception as e:
            self.console.print(f"[red]✗ Error: {str(e)}[/red]")
            self.console.print("[yellow]Tip: Verifique permisos y espacio disponible[/yellow]")

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
                "pasv": "Entrar en modo pasivo",
                "type": "Tipo de transferencia: type <A|I>",
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
            },
            "EXTRAS": {
                "site": "Ejecutar comando específico del sitio: SITE <comando> [args]",
                "appe": "Añadir datos a archivo: APPE <local_path> <remote_path>",
                "abor": "Abortar operación actual",
                "rein": "Reinicializar conexión",
                "nlst": "Listar solo nombres de archivos: NLST [path]",
                "stou": "Almacenar archivo con nombre único: STOU <local_path>"
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
            # Asegurar que estamos en modo pasivo
            self.client.enter_passive_mode()
            
            response = self.client.get_current_dir()
            # Extraer el path entre comillas y limpiarlo
            import re
            path_match = re.search(r'"([^"]*)"', response)
            if path_match:
                path = path_match.group(1)
                # Limpiar múltiples barras y asegurar formato correcto
                path = path.replace('//', '/')
                if not path or path == '/':
                    self.console.print("[cyan]Directorio actual: /[/cyan] (directorio raíz)")
                else:
                    self.console.print(f"[cyan]Directorio actual: {path}[/cyan]")
            else:
                self.console.print(f"[cyan]{response}[/cyan]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_cwd(self, arg):
        """Cambia el directorio de trabajo: CWD <path>"""
        if not arg:
            self.console.print("[red]Error: Uso: CWD <path>[/red]")
            return
        try:
            response = self.client.change_dir(arg)
            
            # Mostrar el directorio actual después del cambio
            try:
                # Obtener y mostrar el nuevo directorio
                pwd_response = self.client.get_current_dir()
                path_match = re.search(r'"([^"]*)"', pwd_response)
                if path_match:
                    current_path = path_match.group(1).replace('//', '/')
                    self.console.print("[green]✓ Directorio cambiado exitosamente[/green]")
                    self.console.print(f"[cyan]Directorio actual: {current_path}[/cyan]")
                else:
                    self.console.print("[green]✓ Directorio cambiado exitosamente[/green]")
            except:
                # Si hay error al obtener el path, al menos confirmar el cambio
                self.console.print("[green]✓ Directorio cambiado exitosamente[/green]")
            
        except Exception as e:
            # Extraer solo el mensaje de error sin el código
            error_msg = str(e)
            if " - " in error_msg:
                error_msg = error_msg.split(" - ")[1]
            self.console.print(f"[red]Error: {error_msg}[/red]")
            self.console.print("[yellow]Tip: Verifique que el directorio existe y tiene permisos[/yellow]")

    def do_cdup(self, arg):
        """Cambia al directorio padre"""
        try:
            response = self.client.change_to_parent_dir()
            
            # Mostrar el directorio actual después del cambio
            try:
                # Obtener y mostrar el nuevo directorio
                pwd_response = self.client.get_current_dir()
                path_match = re.search(r'"([^"]*)"', pwd_response)
                if path_match:
                    current_path = path_match.group(1).replace('//', '/')
                    self.console.print("[green]✓ Cambiado al directorio superior[/green]")
                    self.console.print(f"[cyan]Directorio actual: {current_path}[/cyan]")
                else:
                    self.console.print("[green]✓ Cambiado al directorio superior[/green]")
            except:
                # Si hay error al obtener el path, al menos confirmar el cambio
                self.console.print("[green]✓ Cambiado al directorio superior[/green]")
                
        except Exception as e:
            # Extraer solo el mensaje de error sin el código
            error_msg = str(e)
            if " - " in error_msg:
                error_msg = error_msg.split(" - ")[1]
            self.console.print(f"[red]Error: {error_msg}[/red]")

    def do_mkd(self, arg):
        """Crea un directorio: MKD <path>"""
        try:
            response = self.client.make_dir(arg)
            self.console.print(f"[green]✓ {response}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_rmd(self, arg):
        """Elimina un directorio: RMD <path>"""
        if not arg:
            self.console.print("[red]Error: Uso: RMD <path>[/red]")
            return
            
        try:
            response = self.client.remove_dir(arg)
            if "250" in response:
                self.console.print(f"[green]✓ Directorio '{arg}' eliminado correctamente[/green]")
            else:
                self.console.print(f"[red]Error: {response}[/red]")
        except Exception as e:
            error_msg = str(e)
            if " - " in error_msg:
                error_msg = error_msg.split(" - ")[1]
            self.console.print(f"[red]Error: No se pudo eliminar el directorio: {error_msg}[/red]")

    def do_dele(self, arg):
        """Elimina un archivo: DELE <filename>"""
        if not arg:
            self.console.print("[red]Error: Uso: DELE <filename>[/red]")
            self.console.print("[yellow]Ejemplo: dele archivo.txt[/yellow]")
            return
            
        try:
            response = self.client.delete_file(arg)
            if "250" in response:  # Verificar éxito
                self.console.print(f"[green]✓ Archivo '{arg}' eliminado correctamente[/green]")
            else:
                self.console.print(f"[red]Error: {response}[/red]")
        except Exception as e:
            error_msg = str(e)
            if " - " in error_msg:
                error_msg = error_msg.split(" - ")[1]
            self.console.print(f"[red]Error: No se pudo eliminar el archivo: {error_msg}[/red]")
            self.console.print("[yellow]Tip: Verifique que el archivo existe y tiene permisos[/yellow]")

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

    def do_site(self, arg):
        """Ejecuta comando específico del sitio: SITE <comando> [args]"""
        if not arg:
            self.console.print("[red]Error: Uso: SITE <comando> [args][/red]")
            return
        try:
            response = self.client.site_command(arg)
            self.console.print(f"[cyan]{response}[/cyan]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            
    def do_appe(self, arg):
        """Añade datos a un archivo: APPE <local_path> <remote_path>"""
        args = arg.split()
        if len(args) != 2:
            self.console.print("[red]Error: Uso: APPE <local_path> <remote_path>[/red]")
            self.console.print("[yellow]Ejemplo: appe local.txt remoto.txt[/yellow]")
            return

        local_path, remote_path = args
        try:

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("[cyan]Añadiendo datos...", total=None)
                response = self.client.append_file(local_path, remote_path)
                
            if "226" in response:
                self.console.print(f"[green]✓ Datos añadidos exitosamente a '{remote_path}'[/green]")
            else:
                self.console.print(f"[yellow]{response}[/yellow]")

        except Exception as e:
            self.console.print(f"[red]✗ Error: {str(e)}[/red]")
            self.console.print("[yellow]Tip: Verifique permisos y espacio disponible[/yellow]")

    def do_abor(self, arg):
        """Aborta la operación actual: ABOR"""
        try:
            response = self.client.abort()
            self.console.print(f"[yellow]Operación abortada: {response}[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_rein(self, arg):
        """Reinicializa la conexión: REIN"""
        try:
            response = self.client.reinitialize()
            self.console.print(f"[yellow]Conexión reinicializada: {response}[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def do_nlst(self, arg):
        """Lista solo nombres de archivos: NLST [path]"""
        try:
            # Asegurar que estamos en modo pasivo
            self.client.enter_passive_mode()
            
            # Obtener la lista de archivos
            file_list = self.client.list_files(arg).splitlines()
            
            if not file_list:
                self.console.print("[yellow]Directorio vacío o error listando archivos[/yellow]")
                return
            
            # Crear una tabla para mostrar los resultados
            table = Table(show_header=True, header_style="bold magenta", title="Nombres de Archivos")
            table.add_column("Nombre", style="cyan")
            
            # Añadir cada archivo a la tabla
            for filename in file_list:
                if filename.strip():  # Ignorar líneas vacías
                    table.add_row(filename.strip())
            
            # Mostrar la tabla y el total
            self.console.print(table)
            self.console.print(f"[blue]Total: {len(file_list)} elementos[/blue]\n")
            
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")
            self.console.print("[yellow]Tip: Verifique que tiene permisos y la ruta es válida[/yellow]")

    def do_stou(self, arg):
        """Almacena archivo con nombre único: STOU <local_path>"""
        if not arg:
            self.console.print("[red]Error: Uso: STOU <local_path>[/red]")
            self.console.print("[yellow]Ejemplo: stou archivo.txt[/yellow]")
            return

        try:
            # Verificar archivo local
            from pathlib import Path
            if not Path(arg).exists():
                self.console.print(f"[red]Error: El archivo '{arg}' no existe[/red]")
                return

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("[cyan]Subiendo archivo...", total=None)
                response = self.client.store_unique(arg)
                
            if "226" in response:
                # Extraer el nombre generado del mensaje (si está disponible)
                nombre_generado = response.split("Saved as")[-1].strip() if "Saved as" in response else "nombre único"
                self.console.print(f"[green]✓ Archivo subido exitosamente como {nombre_generado}[/green]")
            else:
                self.console.print(f"[yellow]{response}[/yellow]")

        except Exception as e:
            self.console.print(f"[red]✗ Error: {str(e)}[/red]")
            self.console.print("[yellow]Tip: Verifique permisos y espacio disponible[/yellow]")

    def do_pasv(self, arg):
        """Entra en modo pasivo para transferencias"""
        try:
            response = self.client.enter_passive_mode()
            self.console.print(f"[green]✓ {response}[/green]")
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