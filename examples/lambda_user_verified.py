import json
import logging
from pathlib import Path

from golemrpc.core_imports import VerificationMethod, SubtaskVerificationState
from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)


def user_task(args):
    return 0.15

# Golem default installation directory is where we obtain cli_secret and rpc_cert
datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

# Authenticate with localhost:61000 (default) golem node using cli_secret
# and rpc_cert specified
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
    'task':
        {
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

# One-liner to load the `result.txt` file from result's directory
result_txt = [f for f in response['results'] if f.endswith('result.txt')][0]
# For all GLambda type of tasks there is a stringified json inside `result.txt`
data = json.loads(open(result_txt).read())['data']

# If this assertions passes we have correct results
assert data == 0.15

rpc.post({
    'type': 'VerifyResults',
    'task_id': response['task_id'],
    'subtask_id': response['subtask_id'],
    'verdict': SubtaskVerificationState.VERIFIED
})

# Wait for `TaskResults` message
response = rpc.poll(timeout=None)
results = response['results']

print(results)

rpc.post_wait({
    'type': 'Disconnect'
})
