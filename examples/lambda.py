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
    if 'prefix' in args:
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

# Synchronously wait for tasks to execute
response = rpc.post_wait({
    'type': 'CreateMultipleTasks',
    'tasks': [
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
})

# Response for CreateMultipleTasks contains TaskResult objects array
# where each object corresponds (order preserved) to tasks given.
# (order preserved). Example response:
# [{
#   'type': 'TaskResults',
#   'task_id': '0357c464-2ea2-11e9-97f2-15127dda1506',
#   'results': ['0357c464-2ea2-11e9-97f2-15127dda1506-output']
# }, 
# {
#   'type': 'TaskResults',
#   'task_id': '035775e4-2ea2-11e9-940a-15127dda1506',
#   'results': ['035775e4-2ea2-11e9-940a-15127dda1506-output']
# }]
# For GLambda type of tasks each task's result will
# contain 'output' directory with all the results put inside of it.
# It is a Golem legacy thing (keeping backwards compatibility with blender tasks)
# Example directory structure inside output directory.
# .
# |-- 4a4ac3a8-14e0-11e9-89f7-62356f019451-output
# |   `-- output
# |       |-- result.txt
# |       |-- stderr.log
# |       `-- stdout.log
# |-- 4a4b0fd8-14e0-11e9-92dd-62356f019451-output
# |   `-- output
# |       |-- result.txt
# |       |-- stderr.log
# |       `-- stdout.log

print(response)

rpc.post_wait({
    'type': 'Disconnect'
})
