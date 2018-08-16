"""
This file will contain the ssh_config class used by other methods, scripts, and functions.
"""
import datetime
import time
import ping3
from ssh_config.hosts import test_connection, get_host_key
import concurrent.futures as futures
from typing import Set


class SshUser:
    def __init__(self, name: str="", desire_key: bool=False, key_location: str=""):
        self.name = name
        self.desire_key = desire_key
        self.__key_installed = False
        self.key_location = key_location
        self.__last_used = datetime.datetime.now()

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == other.name

    @property
    def key_installed(self):
        return self.__key_installed

    @key_installed.setter
    def key_installed(self, key_installed: bool):
        # TODO: Validate key works
        self.__key_installed = key_installed

    @property
    def last_used(self):
        return self.__last_used

    @last_used.setter
    def last_used(self, value: datetime):
        assert type(value) == datetime
        assert value < datetime.datetime.now()
        self.__last_used = value


class SshConfig:
    def __init__(self, hostname: str="", port: int=22, aliases: Set[str]=None, public_host_key: str="", users: Set[SshUser]=None):
        self.hostname = hostname.lower()
        self.port = port
        if aliases is not None:
            self.__aliases = aliases
        else:
            self.__aliases = set()
        self.__aliases.add(self.hostname)
        self.public_host_key = public_host_key
        if users is not None:
            self.users = users
        else:
            self.users = set()

    def __str__(self):
        return self.hostname

    def __eq__(self, other):
        return self.hostname == other.hostname

    def __hash__(self):
        return hash(self.hostname)

    @property
    def aliases(self):
        return self.__aliases

    @property
    def working_alias(self):
        threads = {}
        with futures.ThreadPoolExecutor(max_workers=len(self.__aliases)) as executor:
            for alias in self.__aliases:
                threads[alias] = (executor.submit(test_connection, alias, self.port))
        for alias in self.__aliases:
            while threads[alias].running():
                time.sleep(0.1)
            try:
                if threads[alias].result():
                    return alias
            except Exception:
                continue
        return None



    @aliases.setter
    def aliases(self, value: Set[str]):
        self.__aliases = set()
        for alias in value:
            self.__aliases.add(alias.lower())

    def add_alias(self, value: str):
        self.__aliases.add(value.lower())

    def ping_test(self):
        threads = {}
        with futures.ThreadPoolExecutor(max_workers=len(self.__aliases)) as executor:
            for alias in self.__aliases:
                threads[alias] = (executor.submit(ping3.ping, alias, timeout=3))
        for alias in self.__aliases:
            while threads[alias].running():
                time.sleep(0.1)
            try:
                if threads[alias].result() is not None:
                    return True
            except Exception:
                continue
        return False

    def validate_public_host_key(self):
        if not test_connection(self.hostname, self.port):
            return False
        elif self.public_host_key != "" and self.public_host_key != get_host_key(self.hostname, self.port):
            return False
        return True

