# Making assert more useful

This project contains two [Ansible][] plugins:

- A replacement for the core library `assert` module.
- The `assertive` stdout callback plugin

## About the assert module

The `assert` module operates very much like the one in the core
library, with two key differences:

- If you specify the option `nonfatal: true`, then `assert` will
  indicate `CHANGED` on assertion failure rather than `FAILED`.

- The plugin will always evaluate all the tests in your `that` array
  (that is, it will continue to evaluate tests even after one has
  failed).  The individual tests and their results are returned in the
  `assertions` key.

- The plugin takes advantage of Ansible's custom statistics
  functionality to count the number of failed/passed/total assertions.

### Example 1

Given the following playbook:

    - hosts: localhost
      tasks:
        - name: test something
          assert:
            that:
              - (1 + 1) == 2
              - '"apples" in "oranges"'
              - true
            msg: something is wrong with something

We would get the following output:

    TASK [test something] ***************************************************************************************
    fatal: [localhost]: FAILED! => {"ansible_stats": {"aggregate": true, "data": {"assertions": 1, "assertions_failed": 1, "assertions_passed": 0}, "per_host": false}, "assertions": [{"assertion": "(1 + 1) == 2", "evaluated_to": true}, {"assertion": "\"apples\" in \"oranges\"", "evaluated_to": false}, {"assertion": true, "evaluated_to": true}], "changed": false, "failed": true, "msg": "something is wrong with something"}

### Example 2

We can see the return value a little better if we add a `debug`
statement.  In this example, we set `nonfatal: true` so that the
assert reports as `CHANGED` rather than `FAILED` (while we could get
similar behavior using `ignore_errors`, you'll see later on that the
`assertive` callback plugin has special support for nonfatal
assertions):

    - hosts: localhost
      tasks:
        - name: test something
          assert:
            nonfatal: true
            that:
              - (1 + 1) == 2
              - '"apples" in "oranges"'
              - true
            msg: something is wrong with something
          register: result

        - debug:
            var: result

Which gets us:

    TASK [debug] ************************************************************************************************
    ok: [localhost] => {
        "result": {
            "ansible_stats": {
                "aggregate": true, 
                "data": {
                    "assertions": 1, 
                    "assertions_failed": 1, 
                    "assertions_passed": 0
                }, 
                "per_host": false
            }, 
            "assertions": [
                {
                    "assertion": "(1 + 1) == 2", 
                    "evaluated_to": true
                }, 
                {
                    "assertion": "\"apples\" in \"oranges\"", 
                    "evaluated_to": false
                }, 
                {
                    "assertion": true, 
                    "evaluated_to": true
                }
            ], 
            "changed": false, 
            "failed": true, 
            "msg": "something is wrong with something"
        }
    }

## About the assertive callback plugin

The `assertive` callback plugin operates very much like the default
stdout callback plugin, but contains special support for the `assert`
module.

### Example 3

If we have a task similar to that in the previous example:

    - hosts: localhost
      tasks:
        - name: test something
          assert:
            nonfatal: true
            that:
              - (1 + 1) == 2
              - '"apples" in "oranges"'
              - true
            msg: something is wrong with something

And use the following `ansible.cfg`:

    [defaults]
    stdout_callback = assertive
    show_custom_stats = 1

We would get the following output:

    TASK [test something] ***************************************************************************************
    passed: [localhost]  ASSERT((1 + 1) == 2)
    failed: [localhost]  ASSERT("apples" in "oranges")
    passed: [localhost]  ASSERT(True)
    failed: something is wrong with something

    PLAY RECAP **************************************************************************************************
    localhost                  : ok=2    changed=1    unreachable=0    failed=0   


    CUSTOM STATS: ***********************************************************************************************

      RUN: { "assertions": 1,  "assertions_failed": 1,  "assertions_passed": 0}

We will also find the file `testresult.yml` in our current directory
with the following contents:

    stats:
      assertions: 3
      assertions_failed: 1
      assertions_passed: 2
      assertions_skipped: 0
    tests:
    - name: localhost
      tests:
      - assertions:
        - test: (1 + 1) == 2
          testresult: passed
        - test: '"apples" in "oranges"'
          testresult: failed
        - test: true
          testresult: passed
        msg: something is wrong with something
        name: test something
        testresult: failed
        testtime: '2017-07-22T12:53:35.256955'
    timing:
      test_finished_at: '2017-07-22T12:53:35.259489'
      test_started_at: '2017-07-22T12:53:34.386409'
