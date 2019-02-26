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
    # Give some unique name to the task
    "name": "{}".format(str(uuid.uuid1())[:8]),
    "timeout": "0:10:00",
    "subtask_timeout": "0:09:50",
    "subtasks_count": 1,
    "bid": 1.0,
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
# Golem default installation directory is where we obtain cli_secret and rpc_cert
datadir = '{home}/Projects/golem/node_A/rinkeby'.format(home=Path.home())

# Authenticate with localhost:61000 (default) golem node using cli_secret
# and rpc_cert specified
rpc = RPCComponent(
    cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)

rpc.start()

# Ignore TaskCreatedEvent
_ = rpc.post_wait({
    'type': 'CreateTask',
    'task': blender_dict
})

response = rpc.poll(timeout=None)
print(response['results'])

# Tell RPCComponent to disconnect with remote Golem
rpc.post_wait({
    'type': 'Disconnect'
})
