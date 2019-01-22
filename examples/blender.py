import os
import logging
import uuid
from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)

# Authenticate with aws golem node on 61000 port (default) using cli_secret
# and rpc_cert specified
c = RPCComponent(
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
        # Specify where the input can be found
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

c.start()

results = c.post({
    'type': 'map',
    't_dicts': [blender_dict]
})

print(results)

# Tell RPCComponent to disconnect with remote Golem
c.post({
    'type': 'exit'
})
