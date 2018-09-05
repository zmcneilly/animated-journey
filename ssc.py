import argparse
import re
import os
import ssh_config
import paramiko
import getpass

from pathlib import Path
from ssh_config.hosts import ping


def prompt_for_input(prompt: str="Continue? [y/n]"):
    resp = input(prompt).lower().strip()
    if resp[0] == "y":
        return True
    elif resp[0] == "n":
        return False
    else:
        print("Invalid input")
        return prompt_for_input(prompt)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, help="Port to connect to", default=22)
    parser.add_argument("--binary", type=str, default="/usr/bin/ssh", help="SSH binary to use")
    parser.add_argument("--key", type=str, default="", help="SSH Key to install on remote host")
    parser.add_argument("--output", help="Bash script to write to")
    parser.add_argument('connection_string', type=str, help="SSH Connection string")
    return parser.parse_args()


def open_ssh_key(path: str, password: str=None) -> (paramiko.pkey.PKey, str):
    """
    Function will return the Pkey object for the path specified
    :param path: The path to the Pkey object
    :param password: (Optional) The password for the private key
    :return: Loaded Pkey
    """
    with open(path, "r") as __f:
        for key_type in [paramiko.DSSKey, paramiko.RSAKey, paramiko.ECDSAKey]:
            try:
                key_type.from_private_key(__f)
            except paramiko.PasswordRequiredException:
                if password is None:
                    password = getpass.getpass("SSH Key password: ")
            try:
                return key_type.from_private_key(__f, password), password
            except paramiko.SSHException:
                pass


def main():
    # Handle arguments
    args = parse_args()
    match = re.search(r'^(?:([^@]+)@)?(.*)$', args.connection_string)
    hostname = match.group(2)
    username = match.group(1)
    ssh_args = "-o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"

    # Do inital setup of host and user
    if username is None or username == "":
        username = os.environ["USER"]
    if not ping(hostname):
        if not prompt_for_input("{} not responding; continue? [y/n]".format(hostname)):
            raise ConnectionError("Cannot reach {}".format(hostname))
    host_config = ssh_config.load_host_configuration_file(hostname)
    user_config = ssh_config.SshUser(username)
    if host_config is None:
        pub_key = ssh_config.get_host_key(hostname, args.port)
        host_config = ssh_config.SshConfig(hostname, args.port, public_host_key=pub_key, users={user_config})
    for user in host_config.users:
        if user.name == username:
            user_config = user

    # Validate the SSH host key
    if not host_config.validate_public_host_key():
        if prompt_for_input("Public key doesn't match records; continue? [y/n]"):
            host_config.public_host_key = ssh_config.get_host_key(host_config.working_alias, host_config.port)
        else:
            raise ConnectionError("Public host key is wrong! Aborting")

    # Check if key was specified at the command line
    if args.key != "":
        user_config.key_location = str(Path(args.key).resolve())
        user_config.desire_key = True
    while not host_config.validate_login(user_config):
        user_config.passwd = getpass.getpass("Can't authenticate. {con_str}'s password: ".format(con_str=args.connection_string))
        host_config.users.update({user_config})

    # Paramiko, at least, has access.
    # Handle key installation
    if user_config.desire_key and Path(user_config.key_location).exists():
        priv_key, priv_key_password = open_ssh_key(user_config.key_location, user_config.key_password)
        pub_key = priv_key.get_base64()
        if priv_key_password is not None:
            user_config.key_password = priv_key_password
        ssh = host_config.get_ssh_connection(user_config)
        sftp = ssh.open_sftp()

    # Create bash script
    with open(str(Path(args.output).resolve()), "w") as __f:
        connection = "{ssh} {arguments} {user}@{host}\n\n".format(ssh=args.binary,
                                                                  arguments=ssh_args,
                                                                  user=user_config.name,
                                                                  host=host_config.working_alias)
        __f.write("#!/bin/bash\n\n")
        __f.write(connection)

    # Save any changes
    host_config.users.update({user_config})
    ssh_config.add_to_configuration(host_config)


if __name__ == "__main__":
    main()