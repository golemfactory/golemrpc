import asyncio
import copy
import os
import uuid

from autobahn.asyncio.wamp import Session

from ..core_imports import TaskOp


class TransferManager(object):
    def __init__(self, session, meta):
        self.session = session
        self.chunk_size = meta['chunk_size']

    async def _upload_dir(self, dir_path, dest):
        # TODO provide comments 
        absolute_root = os.path.split(os.path.normpath(dir_path))[0]
        await self.session.call('fs.mkdir', 
            os.path.join(
                dest, 
                os.path.basename(os.path.normpath(dir_path))
            )
        )
        for root, dirs, files in os.walk(dir_path):
            for directory in dirs:
                await self.session.call('fs.mkdir',
                    os.path.join(
                            dest,
                            os.path.relpath(root, absolute_root),
                            directory
                    )
                )
            for filename in files:
                await self.upload(
                    os.path.join(root, filename),
                    os.path.join(
                        dest,
                        os.path.relpath(root, absolute_root),
                        filename
                    )
                )

    async def upload(self, filename, dest):
        if os.path.isdir(filename):
            return await self._upload_dir(filename, dest)
        upload_id = await self.session.call('fs.upload_id', dest)
        with open(filename, 'rb') as f:
            while True:
                data = f.read(self.chunk_size)

                if not data:
                    break
                count = await self.session.call('fs.upload', upload_id, data)
                if count != len(data):
                    raise RuntimeError('Error uploading data, lenghts do not match')

                if len(data) < self.chunk_size:
                    break

    async def download(self, filename, dest):
        if await self.session.call('fs.isdir', filename):
            os.mkdir(dest)
            file_list =  await self.session.call('fs.listdir', filename)
            for f in file_list:
                await self.download(
                    os.path.join(filename, f), 
                    os.path.join(dest, f)
                )
            return 
        download_id = await self.session.call('fs.download_id', 
                                         filename)
        with open(dest, 'wb') as f:
            while True:
                data = await self.session.call('fs.download', download_id)
                f.write(data)

                if len(data) != self.chunk_size:
                    break

class TaskMapRemoteFSDecorator(object):

    MAX_SIZE=524288

    def __init__(self, taskmap_handler):
        self.taskmap_handler = taskmap_handler


    async def __call__(self, session: Session, obj):
        meta = await session.call('fs.meta')
        transfer_mgr = TransferManager(session, meta)

        _syspath = await session.call('fs.getsyspath', '')

        # Replace 'resources' for each task_dict
        for d in obj['t_dicts']:

            if not 'resources' in d:
                continue

            # Original 'resources' will be replaced with _resources
            # pointing to remote host filesystem
            _resources = []

            # For each task we create a separate tmpdir on remote
            d['tempfs_dir'] = 'temp_{}'.format(uuid.uuid4())

            # Create directory on remote
            await session.call('fs.mkdir', d['tempfs_dir'])

            # Upload each resource to remote
            for r in d['resources']:
                # normpath is added in ca
                remote_path = os.path.join(d['tempfs_dir'], 
                                           os.path.normpath(os.path.basename(r)))
                await transfer_mgr.upload(r, remote_path)
                _resources.append(os.path.join(_syspath, remote_path))

            d['resources'] = _resources

        results = await self.taskmap_handler(session, obj)
        download_futures = []

        for task_id, task_results in results:
            task_result_path = os.path.join(task_id[:4] + '-output')
            os.mkdir(task_result_path)
            for result in task_results:
                download_futures.append(
                    transfer_mgr.download(result, 
                                          os.path.join(task_result_path, os.path.basename(result)))
                )

        await asyncio.gather(*download_futures)

        purge_futures = []
        for task_id, task_result_dir in results:
            purge_futures.append(
                session.call('comp.task.results_purge', task_id)
            )

        await asyncio.gather(*purge_futures)

        return [
            task_id[:4] + '-output'
            for task_id, task_results in results
        ]
        # TODO Add removing d['tempfs_dir'] after completion

class TaskMapHandler(object):
    def __init__(self, logger, polling_interval=0.5):
        self.event_arr = []
        self.polling_interval = polling_interval
        self.logger = logger

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
        self.logger.info(TaskOp(op_value))
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

        return (task_id, await session.call('comp.task.result', task_id))

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))
