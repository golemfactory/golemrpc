import json
import logging
from pathlib import Path

from golemrpc.core_imports import VerificationMethod, SubtaskVerificationState
from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)

EXPECTED_TASK_RESULT = 'task_result'


def user_task(args):
    '''Dummy task to compute provider side
    '''
    return EXPECTED_TASK_RESULT

# Golem default installation directory is where we obtain cli_secret and rpc_cert
# required for establishing connection with remote Golem.
datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

# cli_secret and rpc_cert paths specified below are default for typical Golem installation.
rpc = RPCComponent(
    cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)

rpc.start()

# 1. User creates a task with verification of type EXTERNALLY_VERFIED
# 2. User acquires `task_id` from TaskCreatedEvent to later track
# the results of his task
# 3. User verifies the results and responds with 'VerifyResults' message
# with appropriate `verdict` set.
# 4. User receives `TaskResults` message

response = rpc.post_wait({
    'type': 'CreateTask',
    'task': {
        'type': 'GLambda',
        'method': user_task,
        'timeout': '00:10:00',
        'resources': ['{home}/my_input.txt'.format(home=Path.home())],
        'verification': {
            'type': VerificationMethod.EXTERNALLY_VERIFIED
        }
    }
})

assert response['type'] == 'TaskCreatedEvent'
task_id = response['task_id']

response = rpc.poll(timeout=None)

assert response['type'] == 'VerificationRequired'
assert response['task_id'] == task_id

# One-liner to load the `result.json` file from result's directory
result_json = [f for f in response['results'] if f.endswith('result.json')][0]
# Load the file and parse JSON object inside of it.
j_obj = json.loads(open(result_json).read())

# Check if there were no errors during computation
assert 'error' not in j_obj

# Actual result is in 'data' field.
data = j_obj['data']

# Verify result
assert data == EXPECTED_TASK_RESULT

rpc.post({
    'type': 'VerifyResults',
    'task_id': response['task_id'],
    'subtask_id': response['subtask_id'],
    'verdict': SubtaskVerificationState.VERIFIED
})

# Wait for `TaskResults` message
response = rpc.poll(timeout=None)

# A single response for CreateTask contains TaskResult object
# for given task. Example response:
# {
#   'type': 'TaskResults',
#   'task_id': '0357c464-2ea2-11e9-97f2-15127dda1506',
#   'results': [
#       '0357c464-2ea2-11e9-97f2-15127dda1506-output/result.json',
#       '0357c464-2ea2-11e9-97f2-15127dda1506-output/stdout.log',
#       '0357c464-2ea2-11e9-97f2-15127dda1506-output/stderr.log'
#   ]
#   'task': task_object
# }

print(response['results'])

rpc.post_wait({
    'type': 'Disconnect'
})
