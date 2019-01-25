import os
import uuid
from pathlib import Path, PurePath

from golemrpc.rpccomponent import RPCComponent
from utils import create_rpc_component


def test_blender():
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
    c = create_rpc_component()

    c.start()

    results = c.post_wait({
        'type': 'map',
        't_dicts': [blender_dict]
    })

    print(results)

    # Tell RPCComponent to disconnect with remote Golem
    c.post_wait({
        'type': 'exit'
    })
