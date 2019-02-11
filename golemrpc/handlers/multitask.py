import asyncio

from ..handlers.task import TaskMessageHandler, TaskRemoteFSDecorator,\
    TaskRemoteFSMappingDecorator


class MultipleTasksMessageHandler():
    async def __call__(self, context, message):
        futures = []

        for t in message['tasks']:
            handler = TaskRemoteFSDecorator(
                TaskRemoteFSMappingDecorator(
                    TaskMessageHandler()
                )
            )
            futures.append(handler(context, {'task': t}))

        return await asyncio.gather(*futures)
