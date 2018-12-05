import asyncio
import os
import uuid
from pathlib import Path

from golemrpc.taskrunner import GolemTaskRunner
from golemrpc.helpers import get_golem_datadir

loop = asyncio.get_event_loop()

# FIXME: Blender example is broken for now: RPC task.status.outputs is empty
# It has to be fixed on golem core side

# Golem Core must be running on localhost
client = GolemTaskRunner(loop, get_golem_datadir())

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

f = client.run(blender_dict)

result = loop.run_until_complete(f)

print(result)