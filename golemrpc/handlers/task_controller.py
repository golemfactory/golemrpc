from ..core_imports import VerificationMethod
from .task import TaskHandler, RemoteTaskHandler


class TaskController:
    def __init__(self):
        # Task handlers storage. Basic state machines
        # handling task creation, result retrieval and status reporting.
        self.tasks = dict()

    async def __call__(self, context, message):
        if message['type'] == 'CreateTask':
            task = RemoteTaskHandler(context) if context.remote else TaskHandler(context)
            await task.on_message(message)
            self.tasks[task.task_id] = task
        else:
            await self.tasks[message['task_id']].on_message(message)
