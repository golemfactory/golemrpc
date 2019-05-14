import logging
from pathlib import Path
import os

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


# Create an RPC component connected to our AWS hosted Golem. 
rpc = RPCComponent(
    host='35.158.100.160',
    cli_secret_filepath='golemcli_aws.tck',
    rpc_cert_filepath='rpc_cert_aws.pem'
)

# Here a separate thread for RPC is created.
# Now user can send messages to the RPC Component to interact with
# remote Golem node.
rpc.start()

rpc.post({
    'type': 'CreateTask',
    'task': {
        'type': 'GLambda',
        'options': {
            'method': my_task,
            'args': {'prefix': 'myprefix_string '},
        },
        'resources': ['{cwd}/my_input.txt'.format(cwd=os.getcwd())],
        'timeout': '00:10:00'
    }
})

_task_created_evt = rpc.poll(timeout=None)
_glambda_app_data = rpc.poll(timeout=None)

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
