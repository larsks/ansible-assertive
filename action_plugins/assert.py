# This file is part of ansible_assertive
#
# The ansible_assertive plugin is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# The ansible_assertive plugin is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os

from ansible.errors import AnsibleError
from ansible.playbook.conditional import Conditional
from ansible.plugins.action import ActionBase
from ansible.module_utils.six import string_types
from ansible.module_utils.parsing.convert_bool import boolean


class ActionModule(ActionBase):
    ''' Fail with custom message '''

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset((
        'fail_msg', 'msg', 'quiet', 'success_msg', 'that',
        'fatal'))

    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)

        self.fail_verbose = (
            os.environ.get(
                'ASSERTIVE_FAIL_VERBOSE', '0').lower()
            in ['1', 'yes', 'true'])

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        if 'that' not in self._task.args:
            raise AnsibleError('conditional required in "that" string')

        fail_msg = None
        success_msg = None

        fail_msg = self._task.args.get('fail_msg', self._task.args.get('msg'))
        if fail_msg is None:
            fail_msg = 'Assertion failed'
        elif isinstance(fail_msg, list):
            if not all(isinstance(x, string_types) for x in fail_msg):
                raise AnsibleError('Type of one of the elements in fail_msg or msg list is not string type')
        elif not isinstance(fail_msg, (string_types, list)):
            raise AnsibleError('Incorrect type for fail_msg or msg, expected a string or list and got %s' % type(fail_msg))

        success_msg = self._task.args.get('success_msg')
        if success_msg is None:
            success_msg = 'All assertions passed'
        elif isinstance(success_msg, list):
            if not all(isinstance(x, string_types) for x in success_msg):
                raise AnsibleError('Type of one of the elements in success_msg list is not string type')
        elif not isinstance(success_msg, (string_types, list)):
            raise AnsibleError('Incorrect type for success_msg, expected a string or list and got %s' % type(success_msg))

        quiet = boolean(self._task.args.get('quiet', False), strict=False)

        # make sure the 'that' items are a list
        thats = self._task.args['that']
        if not isinstance(thats, list):
            thats = [thats]

        # Now we iterate over the that items, temporarily assigning them
        # to the task's when value so we can evaluate the conditional using
        # the built in evaluate function. The when has already been evaluated
        # by this point, and is not used again, so we don't care about mangling
        # that value now
        cond = Conditional(loader=self._loader)
        results = []

        if not quiet:
            result['_ansible_verbose_always'] = True

        for that in thats:
            cond.when = [that]
            test_result = cond.evaluate_conditional(templar=self._templar, all_vars=task_vars)
            this_result = {
                'evaluated_to': test_result,
                'assertion': that,
            }

            results.append(this_result)

        failed = any(not result['evaluated_to'] for result in results)
        changed_when_failed = not self._task.args.get('fatal', False)

        result.update({
            'assertions': results,
            'changed': (failed and changed_when_failed),
            'failed': (failed and not changed_when_failed),
            'ansible_stats': {
                'data': {
                    'assertions': 1,
                    'assertions_failed': 1 if failed else 0,
                    'assertions_passed': 0 if failed else 1,
                },
                'aggregate': True,
                'per_host': True,
            },
        })

        if failed and self.fail_verbose:
            result['_ansible_verbose_always'] = True

        if failed:
            result['msg'] = fail_msg
        elif not failed:
            result['msg'] = success_msg

        return result
