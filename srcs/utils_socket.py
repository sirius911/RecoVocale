import socket


def check_server_status(host:str, port:int) -> bool:
        try:
            sock = socket.create_connection((host, port), timeout=2)
            sock.close()
            return True
        except (socket.timeout, ConnectionRefusedError, socket.gaierror, OSError):
            return False
