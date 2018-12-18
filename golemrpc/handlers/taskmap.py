import asyncio

from autobahn.asyncio.wamp import Session

from ..core_imports import TaskOp

class TaskMapHandler(object):
    def __init__(self):
        self.event_arr = []

    async def __call__(self, session: Session, obj):
        await session.subscribe(self.on_task_status_update,
            u'evt.comp.task.status')

        futures = [
            session.call('comp.task.create', d) for d in obj['t_dicts']
        ]

        creation_results = await asyncio.gather(*futures)

        if any(error != None for _, error in creation_results):
            raise Exception(creation_results)

        futures = [
            self.collect_task(session, task_id) for task_id, _ in creation_results
        ]

        return await asyncio.gather(*futures)

    async def on_task_status_update(self, task_id, subtask_id, op_value):
        # Store a tuple with all the update information
        self.event_arr.append(
            (task_id, subtask_id, TaskOp(op_value))
        )

    async def collect_task(self, session, task_id):
        # Active polling, not optimal but trivial
        related_evts = []

        while True:
            # Task API polling
            await asyncio.sleep(0.5)

            # Get task_id related evts from all events
            related_evts = list(filter(lambda evt: evt[0] == task_id, self.event_arr))

            if any(TaskOp.is_completed(op) for _, _, op in related_evts):
                self.clear_task_evts(task_id)
                break

        return  await session.call('comp.task.result', task_id)

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))