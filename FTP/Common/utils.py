from pathlib import Path
from typing import Optional, Tuple

def validate_transfer_type(type_char: str, format_char: str = None) -> bool:
    """Valida los parámetros del comando TYPE."""
    valid_types = {'A', 'E', 'I', 'L'}
    valid_formats = {'N', 'T', 'C'}
    if type_char not in valid_types:
        return False
    if type_char == 'L' and not (format_char and format_char.isdigit() and 1 <= int(format_char) <= 8):
        return False
    if format_char and type_char in {'A', 'E'} and format_char not in valid_formats:
        return False
    return True

def validate_transfer_mode(mode: str) -> bool:
    """Valida el modo de transferencia."""
    return mode in {'S', 'B', 'C'}

def validate_structure(structure: str) -> bool:
    """Valida la estructura del archivo."""
    return structure in {'F', 'R', 'P'}

def parse_allocation_size(size_str: str) -> Optional[int]:
    """Valida y parsea el tamaño para ALLO."""
    try:
        size = int(size_str)
        return size if size > 0 else None
    except ValueError:
        return None

def parse_restart_marker(marker: str) -> Optional[int]:
    """Valida y parsea el marcador para REST."""
    try:
        point = int(marker)
        return point if point >= 0 else None
    except ValueError:
        return None

def validate_path(path: str) -> bool:
    """Valida que una ruta sea segura y no contenga caracteres peligrosos."""
    forbidden_chars = ['..', '/', '\\', '*', '?', '"', '<', '>', '|']
    return not any(char in path for char in forbidden_chars)

def parse_list_response(response: str) -> list[dict]:
    """Parsea la respuesta del comando LIST a un formato estructurado."""
    entries = []
    for line in response.splitlines():
        # Formato típico Unix: "drwxr-xr-x 2 root root 4096 Dec 1 12:00 folder"
        parts = line.split(None, 8)
        if len(parts) >= 9:
            entries.append({
                'type': 'd' if parts[0].startswith('d') else '-',
                'permissions': parts[0],
                'links': int(parts[1]),
                'owner': parts[2],
                'group': parts[3],
                'size': int(parts[4]),
                'date': f"{parts[5]} {parts[6]} {parts[7]}",
                'name': parts[8]
            })
    return entries

def validate_file_name(filename: str) -> bool:
    """Valida que un nombre de archivo sea válido."""
    forbidden_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    return (filename and 
            not any(char in filename for char in forbidden_chars) and
            len(filename) <= 255)

def parse_mlsd_response(response: str) -> list[dict]:
    """Parsea la respuesta del comando MLSD (listado en formato máquina)."""
    entries = []
    for line in response.splitlines():
        facts, name = line.strip().split(' ', 1)
        entry = {'name': name}
        for fact in facts.split(';'):
            if '=' in fact:
                key, value = fact.split('=')
                entry[key.lower()] = value
        entries.append(entry)
    return entries

def calculate_file_hash(filepath: str, algorithm: str = 'sha256') -> str:
    """Calcula el hash de un archivo para verificar integridad."""
    import hashlib
    hash_obj = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def validate_port_args(host: str, port: int) -> tuple[str, int]:
    """Valida y formatea argumentos para el comando PORT."""
    import ipaddress
    try:
        ip = ipaddress.ip_address(host)
        if not (0 <= port <= 65535):
            raise ValueError("Puerto fuera de rango")
        # Convierte IP y puerto al formato h1,h2,h3,h4,p1,p2
        h1, h2, h3, h4 = str(ip).split('.')
        p1, p2 = port >> 8, port & 0xFF
        return f"{h1},{h2},{h3},{h4},{p1},{p2}", port
    except Exception as e:
        raise ValueError(f"Argumentos PORT inválidos: {e}")

def parse_size_response(response: str) -> int:
    """Parsea la respuesta del comando SIZE."""
    try:
        # Formato típico: "213 12345"
        size = int(response.split()[1])
        return size if size >= 0 else 0
    except (IndexError, ValueError):
        return 0

def format_file_range(start: int, end: int = None) -> str:
    """Formatea el rango para el comando REST."""
    if end is None:
        return str(start)
    return f"{start}-{end}"

def parse_features_response(response: str) -> dict:
    """Parsea la respuesta del comando FEAT."""
    features = {}
    for line in response.splitlines()[1:-1]:  # Ignorar primera y última línea
        line = line.strip(' *')
        if ' ' in line:
            feat, *params = line.split()
            features[feat] = params
        else:
            features[line] = []
    return features

def validate_site_command(command: str, args: list) -> bool:
    """Valida comandos SITE específicos."""
    valid_commands = {
        'CHMOD': lambda args: len(args) == 2 and args[0].isdigit() and len(args[0]) == 3,
        'UMASK': lambda args: len(args) == 1 and args[0].isdigit() and len(args[0]) <= 4,
        'HELP': lambda args: True
    }
    return command in valid_commands and valid_commands[command](args)
