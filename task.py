import asyncio

from abc import ABC, abstractmethod
from core_imports import TaskOp

class BaseTask(ABC):
    def __init__(self, session):
        self.session = session
        # Events received from subscription to 'evt.comp.task.status'
        self.event_arr = []
        self.subscribed = False

    async def __call__(self, **app_data):
        t_dict = self.render_task_dict(**app_data)

        task_id, error_message = await self.create_task(t_dict)

        if error_message:
            raise RuntimeError('Failed to create task: ' + str(error_message))

        # Subscribe for updates before sending create requests
        if not self.subscribed:
            await self.session.subscribe(self.on_task_status_update,
                u'evt.comp.task.status')
            self.subscribed = True

        future = self.collect_task(task_id)

        return await future

    async def create_task(self, task_data):
        return await self.session.call('comp.task.create', task_data)

    @abstractmethod
    def render_task_dict(self, **app_data):
        pass

    async def on_task_status_update(self, task_id, subtask_id, op_value):
        # Store a tuple with all the update information
        self.event_arr.append(
            (task_id, subtask_id, TaskOp(op_value))
        )

    async def collect_task(self, task_id):
        # Active polling, not optimal but trivial
        related_evts = []

        while True:
            await asyncio.sleep(0.5)

            # Get task_id related evts from all events
            related_evts = list(filter(lambda evt: evt[0] == task_id, self.event_arr))

            if any(TaskOp.is_completed(op) for _, _, op in related_evts):
                self.clear_task_evts(task_id)
                break

        state = await self.session.call('comp.task.state', task_id)
        return state['outputs']

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))

