from abc import ABC, abstractmethod

class Command(ABC):
    @abstractmethod
    def execute(self, server, client_socket, args):
        pass