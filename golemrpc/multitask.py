import asyncio

from .task import BaseTask

class MultiTask(BaseTask):
    async def __call__(self, t_dicts):
        futures = [
            super(MultiTask, self).__call__(t_dict) for
            t_dict in t_dicts
        ]
        return await asyncio.gather(*futures)
