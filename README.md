# Making assert more useful for infrastructure testing

This project contains two [Ansible][] plugins:

- A replacement for the core library `assert` action plugin.
- The `assertive` stdout callback plugin

[ansible]: http://www.ansible.com/

## About the assert module

The `assert` module operates very much like the one in the core
library, with two key differences:

- By default, a failed `assert` will be marked as `changed` rather
  than `failed`.  You can enable the stock behavior by specifying
  `fatal: true`.

- The plugin will always evaluate all the tests in your `that` array
  (that is, it will continue to evaluate tests even after one has
  failed).  The individual tests and their results are returned in the
  `assertions` key.

- The plugin takes advantage of Ansible's custom statistics
  functionality to count the number of failed/passed/total assertions.

### Example 1

Here is a simple playbook that contains two assertions:

<!-- file: examples/ex-001.1/playbook.yml -->
```yaml
- hosts: localhost
  name: example 001.1
  vars:
    fruit:
      - apples
      - oranges
  tasks:
    - name: check that we have lemons
      assert:
        that:
          - "'lemons' in fruit"
        msg: we are missing lemons

    - name: check that we have apples
      assert:
        that:
          - "'apples' in fruit"
        msg: we are missing apples
```

If we run this using the stock behavior, we will see the following:

<!-- example: 001.1 -->
```

PLAY [example 001.1] ***********************************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [check that we have lemons] ***********************************************
fatal: [localhost]: FAILED! => {
    "assertion": "'lemons' in fruit", 
    "changed": false, 
    "evaluated_to": false, 
    "failed": true, 
    "msg": "we are missing lemons"
}

PLAY RECAP *********************************************************************
localhost                  : ok=1    changed=0    unreachable=0    failed=1   

```

That is, playbook execution will abort after the first assertion
failure.  If we activate the replacement `assert` plugin with the
following `ansible.cfg`:

<!-- file: examples/ex-001.2/ansible.cfg -->
```
[defaults]
action_plugins = ../../action_plugins

# we don't need retry files for running examples
retry_files_enabled = no
```

Then we will see that an assertion failure shows up as `changed`
rather than `failed`, allowing playbook execution to continue:

<!-- example: 001.2 -->
```

PLAY [example 001.2] ***********************************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [check that we have lemons] ***********************************************
changed: [localhost]

TASK [check that we have apples] ***********************************************
ok: [localhost]

PLAY RECAP *********************************************************************
localhost                  : ok=3    changed=1    unreachable=0    failed=0   

```

### Example 2

If we follow the `assert` task with a `debug` task, we can see that
the return value from `assert` includes a little more information than
the stock plugin.

<!-- file: examples/ex-002/playbook.yml -->
```yaml
- hosts: localhost
  name: example 002
  vars:
    fruit:
      - apples
      - oranges
  tasks:
    - name: check that we have lemons
      assert:
        that:
          - "'lemons' in fruit"
        msg: we are missing lemons
      register: result

    - debug:
        var: result
```

Running this produces:

<!-- example: 002 -->
```

PLAY [example 002] *************************************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [check that we have lemons] ***********************************************
changed: [localhost]

TASK [debug] *******************************************************************
ok: [localhost] => {
    "result": {
        "ansible_stats": {
            "aggregate": true, 
            "data": {
                "assertions": 1, 
                "assertions_failed": 1, 
                "assertions_passed": 0
            }, 
            "per_host": true
        }, 
        "assertions": [
            {
                "assertion": "'lemons' in fruit", 
                "evaluated_to": false
            }
        ], 
        "changed": true, 
        "failed": false, 
        "msg": "we are missing lemons"
    }
}

PLAY RECAP *********************************************************************
localhost                  : ok=3    changed=1    unreachable=0    failed=0   

```

The return value includes detailed information about the assertion
failure(s) as well as metadata that can be consumed by the [custom
statistics][] support in recent versions of Ansible.

[custom statistics]: http://docs.ansible.com/ansible/latest/intro_configuration.html#show-custom-stats

## About the assertive callback plugin

The `assertive` callback plugin operates very much like the default
stdout callback plugin, but contains special support for the `assert`
module:

- It modifies the output of `assert` tasks to be more readable to
  provide more detail, and

- It gathers per-host, per-play, and per-playbook-run assertion
  statistics, and

- It can write assertion results to a YAML file.

### Example 3

If we have a task similar to that in the first example:

<!-- file: examples/ex-003/playbook.yml -->
```yaml
- hosts: localhost
  name: example 003
  vars:
    fruit:
      - apples
      - oranges
  tasks:
    - name: check that we have lemons
      assert:
        that:
          - "'lemons' in fruit"
        msg: we are missing lemons

    - name: check that we have apples
      assert:
        that:
          - "'apples' in fruit"
        msg: we are missing apples
```

And we activate the `assertive` callback plugin using the following
`ansible.cfg`:

<!-- file: examples/ex-003/ansible.cfg -->
```
[defaults]
action_plugins = ../../action_plugins
callback_plugins = ../../callback_plugins

stdout_callback = assertive
show_custom_stats = yes

# we don't need retry files for running examples
retry_files_enabled = no

[assertive]
# this causes the assertive plugin to write assertion results out
# to a file named "testresult.yml".
results = testresult.yml
```

We see the following output:

<!-- example: 003 -->
```

PLAY [example 003] *************************************************************

TASK [Gathering Facts] *********************************************************
ok: [localhost]

TASK [check that we have lemons] ***********************************************
failed: [localhost]  ASSERT('lemons' in fruit)
failed: we are missing lemons

TASK [check that we have apples] ***********************************************
passed: [localhost]  ASSERT('apples' in fruit)

PLAY RECAP *********************************************************************
localhost                  : ok=3    changed=1    unreachable=0    failed=0   


CUSTOM STATS: ******************************************************************
	localhost: { "assertions": 2,  "assertions_failed": 1,  "assertions_passed": 1}

Writing test results to testresult.yml
```

As you can see, the `assertion` tasks now show details about both
passed and failed assertions.  There are custom statistics available
that show details about passed, failed, and total assertions.

The YAML file written out by the `assertive` plugin looks like
this:

<!-- file: examples/ex-003/testresult.yml -->
```yaml
groups:
- hosts:
    localhost:
      stats:
        assertions: 2
        assertions_failed: 1
        assertions_passed: 1
        assertions_skipped: 0
      tests:
      - assertions:
        - test: '''lemons'' in fruit'
          testresult: failed
        msg: we are missing lemons
        name: check that we have lemons
        testresult: failed
        testtime: '2017-08-04T16:31:07.335280'
      - assertions:
        - test: '''apples'' in fruit'
          testresult: passed
        msg: All assertions passed
        name: check that we have apples
        testresult: passed
        testtime: '2017-08-04T16:31:07.355502'
  name: example 003
  stats:
    assertions: 2
    assertions_failed: 1
    assertions_passed: 1
    assertions_skipped: 0
stats:
  assertions: 2
  assertions_failed: 1
  assertions_passed: 1
  assertions_skipped: 0
timing:
  test_finished_at: '2017-08-04T16:31:07.357265'
  test_started_at: '2017-08-04T16:31:06.648284'
```
