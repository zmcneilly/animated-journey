import unittest
import os
import ssh_config

from pathlib import Path


class TestSshConfig(unittest.TestCase):

    def test_get_configuration_file(self):
        if "SSH_CONFIG" in os.environ:
            os.environ.pop("SSH_CONFIG")
        assert ssh_config.config_files.get_configuration_file() == str(Path(".ssh_config.conf").absolute())
        os.environ["SSH_CONFIG"] = str(Path("/foobar").absolute())
        assert ssh_config.config_files.get_configuration_file() == os.environ["SSH_CONFIG"]




