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
tasks = [
    {
        'type': 'GLambda',
        'method': raspa_task,
        'args': {'mol': mol},
        'timeout': '00:10:00'
    }
    for mol in files_content_arr
]

for t in tasks:
    rpc.post({
        'type': 'CreateTask',
        'task': t
    })


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
