from pathlib import Path

from golemrpc.controller import RPCController
from golemrpc.rpccomponent import RPCComponent

# Task to compute provider side
def raspa_task(args):
    import RASPA2
    import pybel

    mol = pybel.readstring('cif', args['mol'])

    return RASPA2.get_helium_void_fraction(mol)

# RASPA specific code for loading molecule structure files

# List all files
cif_files = [
    filepath.absolute() for filepath in Path('./cifs').glob('*.cif')
]

assert cif_files, 'please run this example from golemrpc/examples directory'

# Pick just two of them
filtered_files = cif_files[18:20]

# Load them into memory
files_content_arr = [
    open(f, 'r').read() for f in filtered_files
]

# Golem default installation directory is where we obtain cli_secret and rpc_cert
datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

# Authenticate with localhost:61000 (default) golem node using cli_secret
# and rpc_cert specified
component = RPCComponent(
    host='35.158.100.16',
    cli_secret='~/tmp/golemrpc-threaded/golemcli.tck',
    rpc_cert='rpc_cert_aws.pem'
)

# Wrap RPC component with a controller class
controller = RPCController(component)

# Start in a separate thread (RPCComponent inherits from threading.Thread)
controller.start()

# Run array of (methods, args) on Golem
results = controller.map(
    methods=[raspa_task for _ in files_content_arr],
    args=[{'mol': mol} for mol in files_content_arr]
)

print(results)

controller.stop()
