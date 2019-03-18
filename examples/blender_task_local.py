import logging
import os
import uuid
from pathlib import Path, PurePath

from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)

# Example assumes 'bmw27_cpu.blend' has been placed in your home directory
cube_blend_path = Path.home() / PurePath('bmw27_cpu.blend')

blender_dict = {
    "type": "Blender",
    "subtasks_count": 4,
    "resources": [
        # Specify where the input can be found
        cube_blend_path.as_posix()
    ],
    "options": {
        "output_path": Path.home().as_posix(),
        "format": "PNG",
        "resolution": [
            400,
            300
        ]
    }
}

# Golem default installation directory is where we obtain cli_secret_filepath and rpc_cert_filepath
datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

# Authenticate with localhost:61000 (default) golem node using cli_secret_filepath
# and rpc_cert_filepath specified
rpc = RPCComponent(
    cli_secret_filepath='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert_filepath='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir),
    # Inform RPCComponent that Golem node is local to the application.
    # Resources will not be unnecessarily uploaded.
    # Field `resources_mapped` in `CreateTask` message will be ignored
    remote=False
)

# Here a separate thread for RPC is created.
# Now user can send messages to this the RPC Component to interact with
# remote Golem node.
rpc.start()

# Ignore TaskCreatedEvent
_ = rpc.post_wait({
    'type': 'CreateTask',
    'task': blender_dict
})

response = rpc.poll(timeout=None)
print(response['results'])

rpc.post({
    'type': 'Disconnect'
})
