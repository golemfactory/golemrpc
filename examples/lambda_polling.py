import logging
from pathlib import Path
import queue

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

rpc.post({
    'type': 'CreateTask',
    'task': {
        # Golem Lambda task is a type where user can provide his own
        # callable object with arguments for provider side computation
        'type': 'GLambda',
        'method': my_task,
        'resources': ['my_input.txt']
    }
})

while True:
    try:
        response = rpc.poll(timeout=1.0)
    except queue.Empty as e:
        pass
    else:
        # Response for CreateTask contains TaskResult object
        # for given task. Example response:
        # {
        #   'type': 'TaskResults',
        #   'task_id': '0357c464-2ea2-11e9-97f2-15127dda1506',
        #   'results': ['0357c464-2ea2-11e9-97f2-15127dda1506-output']
        # }
        # For GLambda type of tasks task result will
        # contain 'output' directory with all the results put inside of it.
        # It is a Golem legacy thing (keeping backwards compatibility
        # with blender tasks) Example directory structure inside output directory:
        # .
        # |-- 4a4ac3a8-14e0-11e9-89f7-62356f019451-output
        # |   `-- output
        # |       |-- result.txt
        # |       |-- stderr.log
        # |       `-- stdout.log
        print(response)
        break

rpc.post_wait({
    'type': 'Disconnect'
})
