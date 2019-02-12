import os
import logging
import uuid
from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)

# Authenticate with aws golem node on 61000 port (default) using cli_secret
# and rpc_cert specified
rpc = RPCComponent(
    host='35.158.100.160',
    cli_secret='golemcli_aws.tck',
    rpc_cert='rpc_cert_aws.pem'
)

# Example assumes 'bmw27_cpu.blend' has been placed in your home directory
cube_blend_path = os.path.join(
    str(Path.home()),
    'bmw27_cpu.blend'
)

blender_dict = {
    "type": "Blender",
    # Give some unique name to the task
    "name": "{}".format(str(uuid.uuid1())[:16]),
    "timeout": "0:10:00",
    "subtask_timeout": "0:09:50",
    "subtasks_count": 1,
    "bid": 1.0,
    "resources": [
        cube_blend_path
    ],
    "options": {
        "output_path": str(Path.home()),
        "format": "PNG",
        "resolution": [
            800,
            600
        ]
    }
}

rpc.start()

results = rpc.post_wait({
    'type': 'CreateTask',
    'task': blender_dict
})['results']

print(results)

# Tell RPCComponent to disconnect with remote Golem
rpc.post_wait({
    'type': 'Disconnect'
})
