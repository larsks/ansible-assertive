import os
import pytest
import shutil
import subprocess
import tempfile
import unittest
import yaml

class TestAssertive(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.mkdtemp(prefix='workspace')
        self.testresult = os.path.join(self.workspace, 'testresult.yml')
        os.environ['ASSERTIVE_RECORD'] = self.testresult

    def tearDown(self):
        shutil.rmtree(self.workspace)

    def test_simple_assert(self):
        subprocess.check_call(['tests/run-test', 'test_simple_assert'])
        with open(self.testresult) as fd:
            result = yaml.load(fd)

        assert result['stats']['assertions'] == 2
        assert result['stats']['assertions_failed'] == 1
        assert result['stats']['assertions_passed'] == 1

    def test_fatal_assert(self):
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call(['tests/run-test', 'test_fatal_assert'])

        with open(self.testresult) as fd:
            result = yaml.load(fd)

        assert result['stats']['assertions'] == 0
