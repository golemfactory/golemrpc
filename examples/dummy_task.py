import logging
import os
from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)


def my_task(args):
    '''Task to compute provider side
    It simply appends user provided prefix to a user provided input file
    If no prefix is provided than the default one is used.
    '''

    # 'my_input.txt' has been placed in `/golem/resources` by
    # specifying 'resources' in CreateTask message
    with open('/golem/resources/my_input.txt', 'r') as f:
        content = f.read()

    # There are two ways for sending back results:
    # 1. Returning a serializable object that will be written
    # to result.json in form:
    # {
    #   'result': serialized_object
    # }
    if args and 'prefix' in args:
        return args['prefix'] + content
    else:
        return 'default prefix ' + content
    # 2. Writing files to '/golem/output' directory.

# Golem default installation directory is where we obtain cli_secret and rpc_cert
# required for establishing connection with remote Golem.
datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

# cli_secret and rpc_cert paths specified below are default for typical Golem installation.
rpc = RPCComponent(
    cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)

# Here a separate thread for RPC is created.
# Now user can send messages to the RPC Component to interact with
# remote Golem node.
rpc.start()

rpc.post({
    'type': 'CreateTask',
    'task': {
        'type': 'GLambda',
        'method': my_task,
        'args': {'prefix': 'myprefix_string '},
        'resources': ['{home}/my_input.txt'.format(home=Path.home())],
        'timeout': '00:10:00'
    }
})

# Ignore task created event
task_created_evt = rpc.poll(timeout=None)

task_results = rpc.poll(timeout=None)

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

print(task_results)

rpc.post({
    'type': 'Disconnect'
})
