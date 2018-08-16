"""
This module exists to help with handling config files.
"""

import pickle
import os
from pathlib import Path
from typing import Set
from ssh_config.ssh_config import SshConfig
from ssh_config.hosts import get_host_key


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
    return str(ssh_config_file.resolve())


def load_configuration_file() -> Set[SshConfig]:
    """
    Returns a list of all known SshConfig objects
    :return: A list of SshConfig objects
    """
    configuration_path = Path(get_configuration_file())
    if configuration_path.exists():
        with open(str(configuration_path.resolve()), "rb") as __f:
            return pickle.load(__f)
    else:
        return set()


def load_host_configuration_file(hostname: str) -> SshConfig:
    """
    Returns the SshConfig referenced but the hostname specified. Returns None if cannot find one.
    :param hostname: The hostname to find.
    :return: The matching SshConfig
    """
    for host_config in load_configuration_file():
        for alias in host_config.aliases:
            if alias == hostname.lower():
                return host_config
    return None


def save_configuration(config: Set[SshConfig]) -> None:
    """
    This function will save the configuration file specified. If the file already exists, the saved file will be merged.
    :param config: A list of SshConfig objects
    :return:
    """
    with open(get_configuration_file(), "wb") as __f:
        pickle.dump(config, __f)


def __load_public_key_configuration_file(public_key: str) -> SshConfig:
    """
    This function will return any configurations for hosts with the matching public key.
    :param public_key: The public key to search for.
    :return: The matching SshConfig file.
    """
    for host_config in load_configuration_file():
        if host_config.public_host_key == public_key:
            return host_config


def add_to_configuration(host_config: SshConfig) -> None:
    """
    This function will add the host_config specified to the configuration file.
    :param host_config:
    :return: None
    """
    global_configs = load_configuration_file()
    existing_config = load_host_configuration_file(host_config.hostname)
    try:
        pkey_config = __load_public_key_configuration_file(get_host_key(host_config.hostname, host_config.port))
    except ConnectionError:
        pkey_config = None
    if existing_config is not None:
        global_configs.add(existing_config)
    elif pkey_config is not None:
        pkey_config.add_alias(host_config.hostname)
        pkey_config.users.update(host_config.users)
        global_configs.remove(pkey_config)
        global_configs.add(pkey_config)
    else:
        global_configs.add(host_config)
    save_configuration(global_configs)

