import asyncio
import os
import uuid
from pathlib import Path

from golemrpc.client import GolemRPCClient
from golemrpc.helpers import get_golem_datadir

loop = asyncio.get_event_loop()

client = GolemRPCClient(loop, get_golem_datadir())

cube_blend_path = os.path.join(
    str(Path.home()),
    'cube.blend'
)

blender_dict = {
    "type": "Blender",
    "name": "{}".format(str(uuid.uuid1())[:8]),
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
            320,
            240
        ]
    }
}

f = client.run(blender_dict)

result = loop.run_until_complete(f)

print(result)