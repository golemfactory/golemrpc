from .task import TaskHandler, UserVerifiedRemoteTaskHandler, \
    RemoteTaskHandler


class TaskController:
    def __init__(self):
        # Task handlers storage. Basic state machines
        # handling task creation, result retrieval and status reporting.
        self.tasks = dict()

    async def __call__(self, context, message):
        if message['type'] == 'CreateTask':
            if context.remote:
                if 'verification' in message['task']:
                    task = UserVerifiedRemoteTaskHandler(context)
                else:
                    task = RemoteTaskHandler(context)
            else:
                task = TaskHandler(context)
            await task.on_message(message)
            self.tasks[task.task_id] = task
        else:
            await self.tasks[message['task_id']].on_message(message)
