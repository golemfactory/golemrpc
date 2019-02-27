import logging
import os
from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)

# Task to compute provider side
# It simply appends user provided prefix to a user provided input file
# If no prefix is provided than the default one is used
def my_task(args):
    # 'my_input.txt' has been placed in `/golem/resources` by
    # specifying 'resources' in CreateTask message
    with open('/golem/resources/my_input.txt', 'r') as f:
        content = f.read()

    # There are two ways for giving back results
    # First is returning a serializable object that will be written
    # to result.txt. This should be smaller then 0.5MB.
    if args and 'prefix' in args:
        return args['prefix'] + content
    else:
        return 'default prefix ' + content
    # Second is writing files to '/golem/output' directory. Those
    # files will be packed and sent back to requestor.

# Golem default installation directory is where we obtain cli_secret and rpc_cert
datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

# Authenticate with golem node using cli_secret
rpc = RPCComponent(
    cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)

rpc.start()

tasks = [
    {
        'type': 'GLambda',
        'method': my_task,
        'args': {},
        'resources': ['{home}/my_input.txt'.format(home=Path.home())],
        'timeout': '00:10:00'
    },
    {
        'type': 'GLambda',
        'method': my_task,
        'args': {'prefix': 'myprefix_string '},
        'resources': ['{home}/my_input.txt'.format(home=Path.home())],
        'timeout': '00:10:00'
    }
]

for t in tasks:
    rpc.post({
        'type': 'CreateTask',
        'task': t
    })

# NOTE: Results may come unordered.

result_responses = []

while len(result_responses) < len(tasks):
    response = rpc.poll(timeout=None)
    if response['type'] == 'TaskResults':
        result_responses.append(response)
    else:
        pass


def order_responses(tasks, responses):
    results = [None] * len(tasks)
    for r in responses:
        results[tasks.index(r['task'])] = r['results']
    return results

results = order_responses(tasks, result_responses)

print(results)

rpc.post_wait({
    'type': 'Disconnect'
})
