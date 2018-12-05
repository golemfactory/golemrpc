import asyncio 

from .base import create_component
from .taskrpc import GolemTaskRPC

class GolemTaskRunner(object):
    def __init__(self, loop, datadir, **kwargs):
        self.loop = loop
        self.datadir = datadir
        self.connector = GolemTaskRPC(
            loop,
            create_component(datadir=datadir, **kwargs)
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
        result_files = results[1]

        results = []
        for f in result_files:
            try:
                with open(f[0], 'r') as res:
                    results.append(res.read())
            except Exception as e:
                results.append(str(e))
        return results