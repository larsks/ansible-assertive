import os
import yaml
import subprocess
import unittest
import pytest
import shutil

class TestAssertive(unittest.TestCase):
    def test_simple_assert(self):
        subprocess.check_call(['tests/run-test', 'test_simple_assert'])
        with open('tests/test_simple_assert/testresult.yml') as fd:
            result = yaml.load(fd)

        assert result['stats']['assertions'] == 2
        assert result['stats']['assertions_failed'] == 1
        assert result['stats']['assertions_passed'] == 1

    def test_fatal_assert(self):
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(['tests/run-test', 'test_fatal_assert'])

        with open('tests/test_fatal_assert/testresult.yml') as fd:
            result = yaml.load(fd)

        assert result['stats']['assertions'] == 0
