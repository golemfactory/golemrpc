from .task import TaskMessageHandler, UserVerifiedRemoteTaskMessageHandler, \
    RemoteTaskMessageHandler


class TaskController:
    def __init__(self):
        # Task handlers storage. Basic state machines
        # handling task creation, result retrieval and status reporting.
        self.tasks = dict()

    async def __call__(self, context, message):
        if message['type'] == 'CreateTask':
            if context.remote:
                if 'verification' in message['task']:
                    task = UserVerifiedRemoteTaskMessageHandler(context)
                else:
                    task = RemoteTaskMessageHandler(context)
            else:
                task = TaskMessageHandler(context)
            await task.on_message(message)
            self.tasks[task.task_id] = task
        else:
            await self.tasks[message['task_id']].on_message(message)
