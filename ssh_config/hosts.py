import socket
import paramiko
import os
from platform   import system as system_name  # Returns the system/OS name
from subprocess import call   as system_call  # Execute a shell command


def test_connection(host: str, port: int=22) -> bool:
    """
    Function will attempt to connect to the host and port.
    :param host: The host to attempt connecting to
    :param port: The port to attempt connecting to
    :return: A bool indicating if the attempt was successful or not.
    """
    sock = socket.socket()
    try:
        sock.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        sock.close()


def get_host_key(host: str, port: int=22) -> str:
    """
    Function will connect to the host specified and return the matching SSH key
    :param host: The host to connect to.
    :param port: The port to connect to.
    :return: The key being servered.
    """
    if not test_connection(host, port):
        raise ConnectionError("Cannot connect to {}:{}".format(host, port))
    sock = socket.socket()
    sock.connect((host, port))
    try:
        trans = paramiko.transport.Transport(sock)
        trans.start_client()
        results = trans.get_remote_server_key()
        trans.close()
        return results.get_base64()
    finally:
        sock.close()


def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Ping command count option as function of OS
    param = '-n' if system_name().lower()=='windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]

    # Pinging
    with open(os.devnull, 'w') as devnull:
        return system_call(command, stderr=devnull, stdout=devnull) == 0
