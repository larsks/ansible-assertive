#!/usr/bin/python

import datetime
import os
import yaml

from ansible import constants as C
from ansible.parsing.yaml.objects import AnsibleUnicode
from ansible.plugins.callback.default import CallbackModule as CallbackModule_default
from ansible.utils.color import stringc

try:
    from ansible.utils.unsafe_proxy import AnsibleUnsafeText
except ImportError:
    from ansible.vars.unsafe_proxy import AnsibleUnsafeText

stats = {
            'assertions': 0,
            'assertions_passed': 0,
            'assertions_skipped': 0,
            'assertions_failed': 0,
}

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
        self.stats = stats.copy()

        self.groups = []
        self.group = None
        self.timing = {}

        self.record = os.environ.get('ASSERTIVE_RECORD')
        self.timing['test_started_at'] = str(datetime.datetime.utcnow().isoformat())

    def start_host(self, hostname):
        self.group['hosts'][hostname] = {
            'stats': stats.copy(),
            'tests': [],
        }

    def start_group(self, name=None):
        self.group = {
            'stats': stats.copy(),
            'hosts': {},
        }

        if name is not None:
            self.group['name'] = name

    def process_assert_result(self, result, skipped=False):
        '''process the results from a single assert: action.  a single 
        assert: may contain multiple tests.'''

        hostname = result._host.get_name()
        if not hostname in self.group['hosts']:
            self.start_host(hostname)
        thishost = self.group['hosts'][hostname]

        def inc_stats(key):
            self.stats[key] += 1
            self.group['stats'][key] += 1
            thishost['stats'][key] += 1

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

            inc_stats('assertions')

            if skipped:
                testresult = 'skipped'
                testcolor = C.COLOR_SKIP
                inc_stats('assertions_skipped')
            elif failed:
                testresult = 'failed'
                testcolor = C.COLOR_ERROR
                inc_stats('assertions_failed')
            else:
                testresult = 'passed'
                testcolor = C.COLOR_OK
                inc_stats('assertions_passed')

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

        thishost['tests'].append(testentry)

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

    def close_group(self):
        self.groups.append(self.group)
        self.group = None

    def v2_playbook_on_play_start(self, play):
        super(CallbackModule, self).v2_playbook_on_play_start(play)
        self.close_group()
        self.start_group(play.get_name())

    def v2_playbook_on_stats(self, stats):
        super(CallbackModule, self).v2_playbook_on_stats(stats)

        self.close_group()
        self.timing['test_finished_at'] = str(datetime.datetime.utcnow().isoformat())

        if self.record is not None:
            self._display.display('Writing test results to %s' % (
                self.record,))

            report = {
                'stats': self.stats,
                'groups': [group for group in self.groups if group is not None],
                'timing': self.timing,
            }

            with open(self.record, 'w') as fd:
                yaml.dump(report, fd, default_flow_style=False)
