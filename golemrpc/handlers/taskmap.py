import asyncio
import copy
import os
import uuid

from autobahn.asyncio.wamp import Session

from ..core_imports import TaskOp

class TaskMapRemoteFSDecorator(object):
    def __init__(self, taskmap_handler):
        self.taskmap_handler = taskmap_handler


    async def __call__(self, session: Session, obj):
        _syspath = await session.call('fs.getsyspath', '')

        # Replace 'resources' for each task_dict
        for d in obj['t_dicts']:

            if not 'resources' in d:
                continue

            # Original 'resources' will be replaced with _resources
            # pointing to remote host filesystem
            # FIXME: We could implement some sort of memory keeping for 
            # unmodified task dicts and restore them after execution.
            _resources = []

            # For each task we create a separate tmpdir on remote
            d['tempfs_dir'] = 'temp_{}'.format(uuid.uuid4())

            # Create directory on remote
            await session.call('fs.mkdir', d['tempfs_dir'])

            # Upload each resource to remote 
            for r in d['resources']:
                # FIXME Add directory support 
                remote_path = os.path.join(d['tempfs_dir'], os.path.basename(r))
                with open(r, 'rb') as f:
                    await session.call('fs.write', 
                                       remote_path,
                                       f.read())
                _resources.append(os.path.join(_syspath, remote_path))

            d['resources'] = _resources

        return await self.taskmap_handler(session, obj)
        # TODO Add removing d['tempfs_dir'] after completion

class TaskMapHandler(object):
    def __init__(self, polling_interval=0.5):
        self.event_arr = []
        self.polling_interval = polling_interval

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
            await asyncio.sleep(self.polling_interval)

            # Get task_id related evts from all events
            related_evts = filter(lambda evt: evt[0] == task_id, self.event_arr)

            if any(TaskOp.is_completed(op) for _, _, op in related_evts):
                self.clear_task_evts(task_id)
                break

        return  await session.call('comp.task.result', task_id)

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))
