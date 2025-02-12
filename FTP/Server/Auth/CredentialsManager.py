import json
import os
import logging
from cryptography.fernet import Fernet
from passlib.hash import bcrypt
from pathlib import Path


class CredentialsManager:
    def __init__(self, credentials_file='credentials.enc', key_file='secret.key', config_file='configuration.json'):
        """
        Inicializa el gestor de credenciales.
        """
        logging.basicConfig(level=logging.INFO)
        self.credentials_file = Path(__file__).parent / credentials_file
        self.config_file = Path(__file__).parent / config_file
        self.key_file = Path(__file__).parent / key_file
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key)
        self.credentials = self._load_credentials()

    def _load_or_generate_key(self) -> bytes:
        """
        Carga la clave del archivo; si no existe, la genera y la guarda.
        """
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            try:
                os.chmod(self.key_file, 0o600)
            except Exception as e:
                logging.warning(f"Advertencia: no se pudieron establecer los permisos en {self.key_file}: {e}")
        return key

    def _save_credentials(self):
        """
        Encripta y guarda las credenciales en el archivo.
        """
        data = json.dumps(self.credentials).encode()
        encrypted_data = self.fernet.encrypt(data)
        with open(self.credentials_file, 'wb') as f:
            f.write(encrypted_data)
        try:
            os.chmod(self.credentials_file, 0o600)
        except Exception as e:
            logging.warning(f"Advertencia: no se pudieron establecer los permisos en {self.credentials_file}: {e}")

    def _create_initial_credentials(self):
        self.credentials = {}

        with open(self.config_file, "r") as config:
            config_data = json.load(config)

        initial_user = config_data.get("initial_user")
        initial_password = config_data.get("initial_password")

        if not initial_user or not initial_password:
            raise ValueError("El archivo de configuración debe contener 'initial_user' y 'initial_password'")

        # Crear el usuario inicial
        hashed_password = bcrypt.hash(initial_password)
        self.credentials[initial_user] = hashed_password
        self._save_credentials()
        print(f"Usuario inicial creado con éxito.")

    def _load_credentials(self) -> dict:
        """
        Carga las credenciales del archivo encriptado.
        Si el archivo no existe o está vacío, devuelve un diccionario vacío.
        """
        if not os.path.exists(self.credentials_file):
            self._create_initial_credentials()
            return self.credentials
        try:
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            if not encrypted_data:
                self._create_initial_credentials()
                return self.credentials
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logging.error(f"Error al cargar credenciales: {e}")
            return {}

    def add_user(self, username: str, password: str):
        """
        Agrega un nuevo usuario con la contraseña proporcionada.
        Lanza ValueError si el usuario ya existe.
        """
        if username in self.credentials:
            raise ValueError("El usuario ya existe.")
        hashed = bcrypt.hash(password)
        self.credentials[username] = hashed
        self._save_credentials()

    def remove_user(self, username: str):
        """
        Elimina un usuario.
        Lanza ValueError si el usuario no existe.
        """
        if username not in self.credentials:
            raise ValueError("El usuario no existe.")
        del self.credentials[username]
        self._save_credentials()

    def reset_password(self, username: str, new_password: str):
        """
        Restablece la contraseña de un usuario.
         """
        if username not in self.credentials:
            raise ValueError("El usuario no existe.")
        self.credentials[username] = bcrypt.hash(new_password)
        self._save_credentials()

    def verify_user(self, username: str, password: str) -> bool:
        """
        Verifica si el usuario existe y la contraseña es correcta.
        """
        if username not in self.credentials:
            return False
        hashed = self.credentials[username]
        return bcrypt.verify(password, hashed)

    def list_users(self) -> list:
        """
        Retorna una lista de usuarios.
        """
        return list(self.credentials.keys())