import logging
from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)


def raspa_task(args):
    # Task to compute provider side (RASPA specific).
    # It's possible to import RASPA2 package on remote side because 
    # it's preinstalled in a docker environment we are about to use to 
    # run this task. Every non standard package has to be installed
    # in the remote environment first.
    import RASPA2
    import pybel

    mol = pybel.readstring('cif', args['mol'])

    return RASPA2.get_helium_void_fraction(mol)

# RASPA specific code for loading molecule structure files
# List all files from ./cifs
cif_files = [
    filepath.absolute() for filepath in Path('./cifs').glob('*.cif')
]

assert cif_files, 'please run this example from a directory where cifs/ exist (examples?)'

# For presentation purpose pick only arandom pair of files
filtered_files = cif_files[18:20]

# Load them into memory
files_content_arr = [
    open(f, 'r').read() for f in filtered_files
]

# Create an RPC component connected to our AWS hosted Golem.
rpc = RPCComponent(
    host='35.158.100.160',
    cli_secret='golemcli_aws.tck',
    rpc_cert='rpc_cert_aws.pem'
)
rpc.start()

# Synchronously wait for tasks to execute.
response = rpc.post_wait({
    'type': 'CreateMultipleTasks',
    'tasks': [
        {
            'type': 'GLambda',
            'method': raspa_task,
            'args': {'mol': mol},
            'timeout': '00:10:00'
        }
        for mol in files_content_arr
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
