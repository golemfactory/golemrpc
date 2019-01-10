import os
from pathlib import Path

from golemrpc.controller import RPCController
from golemrpc.rpccomponent import RPCComponent

# Task to compute provider side
# It simply appends user provided prefix to a user provided input file
# It no prefix is provided than the default one is used
def my_task(args):
    with open('/golem/resources/my_input.txt', 'r') as f:
        content = f.read()
    # There are two ways for giving back results
    # First is returning a serializable object that will be written
    # to result.txt
    if 'prefix' in args:
        return args['prefix'] + content 
    else:
        return 'default prefix ' + content
    # Second is writing to '/golem/output' directory 


# Golem default installation directory is where we obtain cli_secret and rpc_cert
datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

# Authenticate with golem node using cli_secret
component = RPCComponent(
    cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)

# Wrap RPC component with a controller class
controller = RPCController(component)

# Start in a separate thread (RPCComponent inherits from threading.Thread)
controller.start()

# Run array of (methods, args) on Golem
results = controller.map(
    methods=[my_task, my_task],
    args=[{}, {'prefix': 'myprefix_string '}],
    resources=['{home}/my_input.txt'.format(home=Path.home())]
)

# Results point to the directories containing outputs for each task (order preserved)
# For tasks created with controller.map method each task will also
# contain 'output' directory which is a Golem legacy issue (keeping
# backwards compatibility with blender tasks)
# One should expected a result array similiar to: ['{task_id}-output', '{task2_id}-output']
# and a directory tree as following:
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
# |-- blender.py
#

print(results)

controller.stop()
