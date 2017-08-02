#!/usr/bin/python

import datetime
import yaml

from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from ansible.utils.color import stringc
from ansible import constants as C
from ansible.parsing.yaml.objects import AnsibleUnicode
from ansible.vars.unsafe_proxy import AnsibleUnsafeText
from ansible.constants import load_config_file

def unicode_representer(dumper, uni):
    node = yaml.ScalarNode(tag=u'tag:yaml.org,2002:str', value=str(uni))
    return node

yaml.add_representer(unicode, unicode_representer)
yaml.add_representer(AnsibleUnicode, unicode_representer)
yaml.add_representer(AnsibleUnsafeText, unicode_representer)

class CallbackModule(CallbackModule_default):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'assertive'

    def __init__(self, *args, **kwargs):
        super(CallbackModule, self).__init__(*args, **kwargs)
        self.suite = None
        self.tests = []
        self.testlog = None

        cfg, cfgpath = load_config_file()
        if cfg.has_option('assertive', 'results'):
            self.testlog = cfg.get('assertive', 'results')

        self.stats = {
            'assertions': 0,
            'assertions_passed': 0,
            'assertions_skipped': 0,
            'assertions_failed': 0,
        }

        self.timing = {}
        self.timing['test_started_at'] = str(datetime.datetime.utcnow().isoformat())

    def process_assert_result(self, result, skipped=False):
        '''process the results from a single assert: action.  a single 
        assert: may contain multiple tests.'''

        # we get loop results one at a time through
        # v2_playbook_item_on_*, so we can ignore tasks
        # with loop results.
        if 'results' in result._result:
            return

        tests = []
        testentry = {
            'assertions': tests,
            'testtime': datetime.datetime.utcnow().isoformat(),
        }

        if result._task.name:
            testentry['name'] = result._task.name

        if 'item' in result._result:
            testentry['item'] = result._result['item']

        for assertion in result._result.get('assertions', [{}]):
            failed = not assertion.get('evaluated_to', True)

            self.stats['assertions'] += 1

            if skipped:
                testresult = 'skipped'
                testcolor = C.COLOR_SKIP
                self.stats['assertions_skipped'] += 1
            elif failed:
                testresult = 'failed'
                testcolor = C.COLOR_ERROR
                self.stats['assertions_failed'] += 1
            else:
                testresult = 'passed'
                testcolor = C.COLOR_OK
                self.stats['assertions_passed'] += 1

            thistest = {
                'testresult': testresult,
                'test': assertion.get('assertion'),
            }

            tests.append(thistest)

            prefix = stringc('%s: [%s]' % (
                testresult, result._host.get_name()), testcolor)

            self._display.display('%s  ASSERT(%s)' % (
                prefix,
                assertion.get('assertion', '(skipped)')))

        failed = any(test['testresult'] == 'failed'
                     for test in tests)

        skipped = all(test['testresult'] == 'skipped'
                      for test in tests)

        if 'msg' in result._result:
            testentry['msg'] = result._result['msg']
            if failed:
                msg ='failed: %s' % (result._result['msg'])
                self._display.display(stringc(msg, C.COLOR_ERROR))

        if failed:
            testentry['testresult'] = 'failed'
        elif skipped:
            testentry['testresult'] = 'skipped'
        else:
            testentry['testresult'] = 'passed'

        self.suite['tests'].append(testentry)

    def v2_runner_item_on_ok(self, result):
        if result._task.action == 'assert':
            self.process_assert_result(result)
        else:
            super(CallbackModule, self).v2_runner_on_item_ok(result)

    def v2_runner_on_ok(self, result):
        if result._task.action == 'assert':
            self.process_assert_result(result)
        else:
            super(CallbackModule, self).v2_runner_on_ok(result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if not ignore_errors:
            super(CallbackModule, self).v2_runner_on_failed(result, ignore_errors=ignore_errors)
        else:
            self._display.display(stringc('failed (ignored): [%s]' % (
                result._host.get_name(),
            ), C.COLOR_CHANGED))

    def v2_runner_on_skipped(self, result):
        if result._task.action == 'assert':
            self.process_assert_result(result, skipped=True)
        else:
            super(CallbackModule, self).v2_runner_on_skipped(result)

    def v2_runner_item_on_skipped(self, result):
        if result._task.action == 'assert':
            self.process_assert_result(result, skipped=True)
        else:
            super(CallbackModule, self).v2_runner_item_on_skipped(result)

    def close_test_suite(self):
        if self.suite is not None and self.suite['tests']:
            self.tests.append(self.suite)

    def v2_playbook_on_play_start(self, play):
        super(CallbackModule, self).v2_playbook_on_play_start(play)

        self.close_test_suite()
        self.suite = {'name': play.get_name(), 'tests': []}

    def v2_playbook_on_stats(self, stats):
        super(CallbackModule, self).v2_playbook_on_stats(stats)

        self.close_test_suite()
        self.timing['test_finished_at'] = str(datetime.datetime.utcnow().isoformat())

        if self.testlog is not None:
            self._display.display('Writing test results to %s' % (
                self.testlog,))

            report = {
                'stats': self.stats,
                'tests': self.tests,
                'timing': self.timing,
            }

            with open(self.testlog, 'w') as fd:
                yaml.dump(report, fd, default_flow_style=False)
