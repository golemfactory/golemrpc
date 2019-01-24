import asyncio
import copy
import logging
import os
from pathlib import PurePath
import uuid

from autobahn.asyncio.wamp import Session

from ..core_imports import TaskOp


class TransferManager(object):
    def __init__(self, session, meta):
        self.session = session
        self.chunk_size = meta['chunk_size']
        self.path_ser = lambda path: PurePath(path).as_posix()

    async def upload(self, src, dest):
        if os.path.isdir(src):
            await self.session.call('fs.mkdir', self.path_ser(dest))
            file_list = [
                os.path.normpath(f) for f in
                os.listdir(src)
            ]
            for f in file_list:
                await self.upload(
                    os.path.join(src, f),
                    os.path.join(dest, f)
                )
        else:
            await self.upload_file(src, dest)

    async def upload_file(self, src, dest):
        upload_id = await self.session.call('fs.upload_id', self.path_ser(dest))
        with open(src, 'rb') as f:
            while True:
                data = f.read(self.chunk_size)

                if not data:
                    break
                count = await self.session.call('fs.upload', upload_id, data)
                if count != len(data):
                    raise RuntimeError('Error uploading data, lenghts do not match')

                if len(data) < self.chunk_size:
                    break

    async def download(self, src, dest):
        if await self.session.call('fs.isdir', self.path_ser(src)):
            os.mkdir(dest)
            file_list = await self.session.call('fs.listdir', self.path_ser(src))
            file_list[:] = [PurePath(f) for f in file_list]
            for f in file_list:
                await self.download(
                    os.path.join(src, f),
                    os.path.join(dest, f)
                )
        else:
            await self.download_file(src, dest)

    async def download_file(self, src, dest):
        download_id = await self.session.call('fs.download_id',
                                              self.path_ser(src))
        with open(dest, 'wb') as f:
            while True:
                data = await self.session.call('fs.download', download_id)
                f.write(data)

                if len(data) != self.chunk_size:
                    break


class TaskMapRemoteFSDecorator(object):

    def __init__(self, taskmap_handler):
        self.taskmap_handler = taskmap_handler

    async def __call__(self, session: Session, obj):
        meta = await session.call('fs.meta')
        transfer_mgr = TransferManager(session, meta)

        _syspath = PurePath(await session.call('fs.getsyspath', ''))

        # Replace 'resources' for each task_dict
        for d in obj['t_dicts']:

            if 'resources' not in d:
                continue

            # Original 'resources' will be replaced with _resources
            # pointing to remote host filesystem
            _resources = []

            # For each task we create a separate tmpdir on remote
            tempfs_dir = PurePath('temp_{}'.format(uuid.uuid1()))

            # Create directory on remote
            await session.call('fs.mkdir', tempfs_dir.as_posix())
            # Upload each resource to remote
            for r in d['resources']:
                r = PurePath(r)
                remote_path = tempfs_dir / r.name
                await transfer_mgr.upload(r.as_posix(), remote_path.as_posix())
                _resources.append((_syspath / remote_path).as_posix())

            d['resources'] = _resources
            d['tempfs_dir'] = tempfs_dir.as_posix()

        results = await self.taskmap_handler(session, obj)
        download_futures = []

        for task_id, task_results in results:
            task_result_path = os.path.join(task_id + '-output')
            os.mkdir(task_result_path)
            for result in task_results:
                download_futures.append(
                    transfer_mgr.download(result, 
                                          os.path.join(task_result_path, os.path.basename(result)))
                )

        await asyncio.gather(*download_futures)

        purge_futures = []
        for task_id, _ in results:
            purge_futures.append(
                session.call('comp.task.results_purge', task_id)
            )

        await asyncio.gather(*purge_futures)

        return [
            task_id + '-output'
            for task_id, task_results in results
        ]
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

        if any(error is not None for _, error in creation_results):
            raise Exception(creation_results)

        futures = [
            self.collect_task(session, task_id) for task_id, _ in creation_results
        ]

        return await asyncio.gather(*futures)

    async def on_task_status_update(self, task_id, subtask_id, op_value):
        # Store a tuple with all the update information
        logging.info(TaskOp(op_value))
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
            related_evts = list(filter(lambda evt: evt[0] == task_id, self.event_arr))

            if any(op == TaskOp.TIMEOUT for _, _, op in related_evts):
                raise TimeoutError("Task {} timed out".format(task_id))

            if any(TaskOp.is_completed(op) for _, _, op in related_evts):
                self.clear_task_evts(task_id)
                break

        return (task_id, await session.call('comp.task.result', task_id))

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))
