import logging
from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)


def raspa_task(args):
    '''Task to compute provider side (RASPA specific).
    It's possible to import RASPA2 package on remote side because
    it's preinstalled in a docker environment we are about to use to
    run this task. Every non standard package has to be installed
    in the remote environment first.
    '''
    import RASPA2
    import pybel

    mol = pybel.readstring('cif', args['mol'])

    return RASPA2.get_helium_void_fraction(mol)


# RASPA specific code for loading molecule structure files
# List all files from ./raspa_data
cif_files = [
    filepath.absolute() for filepath in Path('./raspa_data').glob('*.cif')
]

assert cif_files, 'please run this example from a directory where raspa_data/ exist (examples?)'

# For presentation purpose pick only arandom pair of files
filtered_files = cif_files[18:20]

# Load them into memory
files_content_arr = [
    open(f, 'r').read() for f in filtered_files
]

# Golem default installation directory is where we obtain cli_secret_filepath and rpc_cert_filepath
# required for establishing connection with remote Golem.
datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

# cli_secret_filepath and rpc_cert_filepath paths specified below are default for typical Golem installation.
rpc = RPCComponent(
    cli_secret_filepath='{datadir}/crossbar/secrets/golemcli.tck'.format(
        datadir=datadir),
    rpc_cert_filepath='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)

rpc.start()

tasks = [
    {
        'type': 'GLambda',
        'options': {
            'method': raspa_task,
            'args': {'mol': mol}
        },
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

# Collect `TaskResults` messages as long as we get a result for each
# task we created.
while len(result_responses) < len(tasks):
    response = rpc.poll(timeout=None)
    if response['type'] == 'TaskResults':
        result_responses.append(response)
    else:
        # There will be other messages in the meantime like: 'TaskCreatedEvent'.
        # We can simply ignore them for our example.
        pass


def order_responses(tasks, responses):
    '''Simple function for ordering TaskResults according to their's
    corresponding task order in `tasks` object.
    This is required because result's may come unordered.
    '''
    results = [None] * len(tasks)
    for r in responses:
        results[tasks.index(r['task'])] = r['results']
    return results


results = order_responses(tasks, result_responses)

print(results)

rpc.post_wait({
    'type': 'Disconnect'
})
