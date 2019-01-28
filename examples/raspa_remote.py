import logging
from pathlib import Path

from golemrpc.controller import RPCController
from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)


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

assert cif_files, 'please run this example from a directory where cifs/ exist (examples?)'

# Pick just two of them
filtered_files = cif_files[18:20]

# Load them into memory
files_content_arr = [
    open(f, 'r').read() for f in filtered_files
]

component = RPCComponent(
    host='35.158.100.160',
    cli_secret='golemcli_aws.tck',
    rpc_cert='rpc_cert_aws.pem'
)

# Wrap RPC component with a controller class
controller = RPCController(component)

# Start in a separate thread (RPCComponent inherits from threading.Thread)
controller.start()

# Map array of (methods, args) to Golem
# Task object (serialized methods + arguments) that will be sent
# to Golem by the controller can not exceed 0.5MB in size. If one
# wants to send more data for computation then `resources`
# key must be used. These resources will be uploaded to
# remote Golem for further handling. Resources must be available
# for read in local file system. Those resources are available to
# user in `/golem/resources` directory (`raspa_task` in this case).

results = controller.map(
    methods=[raspa_task for _ in files_content_arr],
    args=[{'mol': mol} for mol in files_content_arr],
    timeout='00:10:00',
    # resources=['/home/user/input.data', '/home/user/input2.data']
)

# For more information on how results are stored see examples/lambda.py source source
print(results)

controller.stop()
