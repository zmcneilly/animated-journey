import argparse
import re
import os
import ssh_config

from ssh_config.hosts import ping

from pathlib import Path


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
    parser.add_argument("--output", help="Bash script to write to")
    parser.add_argument('connection_string', type=str, help="SSH Connection string")
    return parser.parse_args()


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
    if host_config is None:
        pub_key = ssh_config.get_host_key(hostname, args.port)
        host_config = ssh_config.SshConfig(hostname, args.port, public_host_key=pub_key, users={ssh_config.SshUser(username)})
    for user in host_config.users:
        if user.name == username:
            user_config = user

    # Validate the SSH host key
    try:
        if not host_config.validate_public_host_key():
            if prompt_for_input("Public key doesn't match records; continue? [y/n]"):
                host_config.public_host_key = ssh_config.get_host_key(host_config.working_alias, host_config.port)
            else:
                raise ConnectionError("Public host key is wrong! Aborting")
    finally:
        ssh_config.add_to_configuration(host_config)

    # Create bash script
    with open(str(Path(args.output).resolve()), "w") as __f:
        connection = "{ssh} {arguments} {user}@{host}\n\n".format(ssh=args.binary,
                                                                  arguments=ssh_args,
                                                                  user=user_config.name,
                                                                  host=host_config.working_alias)
        __f.write("#!/bin/bash\n\n")
        __f.write(connection)


if __name__ == "__main__":
    main()