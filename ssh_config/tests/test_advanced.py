import ssh_config
import unittest
import os

from pathlib import Path


class TestSshConfig(unittest.TestCase):

    def test_config_full_cycle(self):
        test_path = Path(".ssh_config_test.json")
        os.environ["SSH_CONFIG"] = str(test_path.absolute())
        if test_path.exists():
            os.remove(str(test_path.absolute()))

        foobar_config = ssh_config.ssh_config.SshConfig("foobar")
        baz_config = ssh_config.ssh_config.SshConfig("baz")

        ssh_config.config_files.add_to_configuration(foobar_config, key="foobar")
        self.assertTrue(test_path.exists())

        loaded_config = ssh_config.config_files.load_configuration_file(key="foobar")
        self.assertTrue(foobar_config in loaded_config)
        self.assertTrue(baz_config not in loaded_config)

        ssh_config.config_files.add_to_configuration(baz_config, key="foobar")

        loaded_config = ssh_config.config_files.load_configuration_file(key="foobar")
        self.assertTrue(foobar_config in loaded_config)
        self.assertTrue(baz_config in loaded_config)

        if test_path.exists():
            os.remove(str(test_path.absolute()))
