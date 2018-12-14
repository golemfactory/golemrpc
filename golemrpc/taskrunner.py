import asyncio 

from .utils import create_component
from .taskrpc import GolemTaskRPC

class GolemTaskRunner(object):
    def __init__(self, loop, **kwargs):
        self.loop = loop
        self.connector = GolemTaskRPC(
            loop,
            create_component(**kwargs)
        )
        
    async def run(self, task):
        results = await asyncio.gather(
            self.connector.start(),
            self.connector.run(task)
        )
        # First result is from connector.start
        # We are not interested in that, it is autobahn's component
        # API problem that we must implement it this way
        # We are interested in run_task results only
        return results[1]
