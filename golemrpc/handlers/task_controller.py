from .task import TaskMessageHandler, UserVerifiedTaskMessageHandler


class TaskController:
    def __init__(self):
        self.tasks = dict()

    async def __call__(self, context, message):
        if message['type'] == 'CreateTask':
            if 'verification' in message['task']:
                task = UserVerifiedTaskMessageHandler(context)
            else:
                task = TaskMessageHandler(context)
            await task.on_message(message)
            self.tasks[task.task_id] = task
        else:
            await self.tasks[message['task_id']].on_message(message)
