import os
import uuid
from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

# FIXME: Blender example is broken for now: RPC task.status.outputs is empty
# It has to be fixed on golem core side

datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

c = RPCComponent(
    cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)

# Example assumes 'cube.blend' has been placed in your home directory
cube_blend_path = os.path.join(
    str(Path.home()),
    'cube.blend'
)

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
        cube_blend_path
    ],
    "options": {
        "output_path": str(Path.home()),
        "format": "PNG",
        "resolution": [
            320,
            240
        ]
    }
}

c.start()

results = c.evaluate_sync({
    'type': 'map',
    't_dicts': [blender_dict]
})

print(results)

c.stop()
