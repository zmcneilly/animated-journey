"""
This module exists to help with handling config files.
"""

import pickle
import os
import getpass
import base64
from cryptography.fernet import Fernet
from pathlib import Path
from typing import Set
from ssh_config.ssh_config import SshConfig
from ssh_config.hosts import get_host_key

PASSWD_PROMPT = "Please enter the password for your configuration here: "
CIPHER = None


def __get_cipher(key: str=None):
    global CIPHER
    if CIPHER is None:
        if key is None:
            key = getpass.getpass("Please enter the password for your configuration file here: ")
        while len(key) < 32:
            key = key + "="
        while len(key) > 32:
            key = key[0:len(key)-2]
        CIPHER = Fernet(base64.urlsafe_b64encode(key.encode('utf-8')))
    return CIPHER


def get_configuration_file() -> str:
    """
    Function will return the absolute path to the configuration file. This will check the "SSH_CONFIG" environment
    variable first, then use "${HOME}/.ssh_config.json" if available, then default to ".ssh_config.json".
    :return: A string with the absolute path to the configuration file.
    """
    ssh_config_file_name = ".ssh_config.conf"
    ssh_config_file = Path(ssh_config_file_name)
    if "SSH_CONFIG" in os.environ:
        ssh_config_file = Path(os.environ["SSH_CONFIG"])
    elif "HOME" in os.environ:
        ssh_config_file = Path("{}/{}".format(os.environ["HOME"], ssh_config_file_name))
    if ssh_config_file.exists():
        result = str(ssh_config_file.resolve())
    else:
        result = str(ssh_config_file.absolute())
    return result


def load_configuration_file(key: str=None) -> Set[SshConfig]:
    """
    Returns a list of all known SshConfig objects
    :return: A list of SshConfig objects
    """
    configuration_path = Path(get_configuration_file())
    if configuration_path.exists():
        cipher = __get_cipher(key)
        with open(str(configuration_path.resolve()), "rb") as __f:
            config_file = __f.read()
            config_file = base64.decodebytes(config_file)
            config_file = cipher.decrypt(config_file)
            return pickle.loads(config_file)
    else:
        return set()


def load_host_configuration_file(hostname: str, key: str=None) -> SshConfig:
    """
    Returns the SshConfig referenced but the hostname specified. Returns None if cannot find one.
    :param hostname: The hostname to find.
    :return: The matching SshConfig
    """
    for host_config in load_configuration_file(key):
        for alias in host_config.aliases:
            if alias == hostname.lower():
                return host_config
    return None


def save_configuration(config: Set[SshConfig], key: str=None) -> None:
    """
    This function will save the configuration file specified. If the file already exists, the saved file will be merged.
    :param config: A list of SshConfig objects
    :return:
    """
    cipher = __get_cipher(key)
    with open(get_configuration_file(), "wb") as __f:
        output = base64.encodebytes(cipher.encrypt(pickle.dumps(config)))
        __f.write(output)


def __load_public_key_configuration_file(public_key: str, key: str=None) -> SshConfig:
    """
    This function will return any configurations for hosts with the matching public key.
    :param public_key: The public key to search for.
    :return: The matching SshConfig file.
    """
    for host_config in load_configuration_file():
        if host_config.public_host_key == public_key:
            return host_config


def add_to_configuration(host_config: SshConfig, key: str=None) -> None:
    """
    This function will add the host_config specified to the configuration file.
    :param host_config:
    :return: None
    """
    global_configs = load_configuration_file(key)
    existing_config = load_host_configuration_file(host_config.hostname, key=key)
    if existing_config is not None:
        global_configs.remove(existing_config)
        existing_config.users.update({host_config.users})
        existing_config.aliases.update({host_config.aliases})
        existing_config.public_host_key = host_config.public_host_key
        global_configs.add(existing_config)
        pkey_config = None
    else:
        try:
            pkey_config = __load_public_key_configuration_file(get_host_key(host_config.hostname, host_config.port), key=key)
        except ConnectionError:
            pkey_config = None
    if pkey_config is not None:
        pkey_config.add_alias(host_config.hostname)
        pkey_config.users.update({host_config.users})
        global_configs.remove(pkey_config)
        global_configs.add(pkey_config)
    else:
        global_configs.add(host_config)
    save_configuration(global_configs, key)

