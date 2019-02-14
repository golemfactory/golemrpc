import asyncio
import copy
import logging
import os
from pathlib import PurePath
import uuid

from autobahn.asyncio.wamp import Session
import marshmallow

from ..core_imports import TaskOp, SubtaskOp
from ..transfermanager import TransferManager

from ..schemas.tasks import GLambdaTaskSchema, TaskSchema


class TaskController:
    def __init__(self):
        self.tasks = dict()

    async def __call__(self, context, message):
        # FIXME Coherent return type

        if message['type'] == 'CreateTask':
            task = TaskMessageHandler(context)
            task_id = await task.on_message(message)
            self.tasks[task_id] = task
            return {
                'type': 'TaskCreatedEvent',
                'task_id': task_id
            }
        else:
            return await self.tasks[message['task_id']].on_message(message)


class RemoteResourceProvider:
    def __init__(self, session, meta):
        self.session = session
        self.meta = meta
        self.transfer_mgr = TransferManager(session, meta)

    async def upload(self, resources, dest_root):
        _syspath = self.meta['syspath']
        _resources = []

        if isinstance(resources, dict):
            for src, dest in resources.items():
                src = PurePath(src)
                if dest:
                    # TODO Can we store those PurePaths in resources_mapped?
                    dest = PurePath(dest)

                    # Support only relative paths. Relation root on provider
                    # side is '/golem/resources'. Absolute paths are not
                    # supported because it's not clear how paths like
                    # 'C:/file.txt' or '/home/user/file.txt' should be handled.
                    assert not dest.is_absolute(), ('only relative paths are allowed '
                                                    'as mapping values {}'.format(dest.as_posix()))

                    parents = list(dest.parents)

                    # Removing last element because it's a root (current
                    # directory, for posix it's '.')
                    parents = [
                        p for p in parents[:-1]
                    ]
                    # Now parents should contain a growing directory sequence
                    # for path 'a/b/c' that will be ['a', 'a/b']

                    if parents:
                        # Recreate directory structure stored in `parents` on remote side
                        for anchor in reversed(parents):
                            await self.session.call('fs.mkdir', (dest_root / anchor).as_posix())
                    remote_path = dest_root / dest
                    await self.transfer_mgr.upload(src.as_posix(), remote_path.as_posix())

                    if parents:
                        # If there is a directory structure defined in mapping
                        # then a resource path should point to it's last anchor e.g.
                        # 'dir1/dir2/foo` should yield `dir1`.
                        resources_dir_path = _syspath / dest_root / parents[-1]
                    else:
                        resources_dir_path = _syspath / dest_root / dest

                    _resources.append(resources_dir_path.as_posix())

                else:
                    remote_path = dest_root / src.name
                    await self.transfer_mgr.upload(src.as_posix(), remote_path.as_posix())
                    _resources.append((_syspath / remote_path).as_posix())

            return _resources

        elif isinstance(resources, list):
            for r in resources:
                r = PurePath(r)
                # Place resources on remote filesystem root directory
                # e.g. 'foo/bar/file.txt' -> '$dest_root/file.txt'
                remote_path = dest_root / r.name
                await self.transfer_mgr.upload(r.as_posix(), remote_path.as_posix())
                # For remote side to pick up resources during task requesting an
                # absolute path to resources has to be put in _resources, e.g.
                # $_syspath = /tmp
                # $dest_root = tempfs1234
                # local resource = foo/bar/file.txt
                # _resource = /tmp/tempfs1234/file.txt
                _resources.append((_syspath / remote_path).as_posix())

            return _resources
        else:
            raise NotImplementedError()

    async def download(self, resources, dest):
        # Download task result to ${task_id}-output directory e.g.
        # if results are equal to ['foo.txt', 'bar.txt'] then resulting
        # directory structure will looks as follows:
        # .
        # `-- ${task_id}-output
        #      |-- foo.txt
        #      |-- bar.txt

        download_futures = []
        for result in resources:
            dest = os.path.join(dest,
                                os.path.basename(result))
            download_futures.append(self.transfer_mgr.download(result, dest))
        await asyncio.gather(*download_futures)

        return [dest]


class TaskRemoteFSDecorator(object):
    '''TaskRemoteFSMappingDecorator allows to recreate task's
    resources on remote side (remote Golem requestor). User
    has to specify `resources` key as usual for golem task dict.
    Those resources will be uploaded to a virtual filesystem on
    remote golem. Key `resources` will be modified to resemble
    remote paths.
    '''
    pass


class TaskRemoteFSMappingDecorator(object):
    '''TaskRemoteFSMappingDecorator allows to recreate task's resources on
    remote in a user defined manner. In other words user can specify
    how his local resources should be structured on a remote host (remote
    Golem node). Consider local relative path 'foo/bar.txt', when this path is
    fed to `resources` in task_dict as usual then user will end up with
    `/golem/resources/bar.txt' because there is no information on how directory
    structure in path should be taken into account. This class allows
    specifying this information, namely user can provide 'resources_mapped'
    dict containing mappings for each resource. Now to recreate the
    structure 'foo/bar.txt' user should define following dictionary:
    'resources_mapped': {
        'foo/bar.txt': 'foo/bar.txt'
    }
    Further in the code the left hand side is called `src` and right hand
    side is called `dest`.
    There is no need to modify or append anything to `resources`, algorithm
    will fill `resources` automatically based on `resources_mapped`.
    '''
    pass


class TaskMessageHandler(object):
    def __init__(self, context, polling_interval=0.5):
        self.context = context
        self.event_arr = []
        self.polling_interval = polling_interval
        self.task = None
        self.task_id = None
        self.tempfs_dir = PurePath('temp_{}'.format(uuid.uuid1()))
        self.serializers = {
            'GLambda': GLambdaTaskSchema(unknown=marshmallow.INCLUDE),
            # Generic serializer
            '_Task': TaskSchema(unknown=marshmallow.INCLUDE)
        }
        self.is_finished = False

    async def on_message(self, message):
        # TODO REFACTOR - isolate code of remoteresourceprovider
        session = self.context.session

        # FIXME create self.Create method
        if message['type'] == 'CreateTask':
            # An exception is thrown if something is wrong with
            # the task format

            meta = await session.call('fs.meta')
            # FIXME Is this serialized to string or some cbor/msgpack??
            if len(str(self.task)) > meta['chunk_size']:
                raise ValueError('serialized task exceeds maximum chunk_size {}\
                    consider using \'resources\' to transport bigger files'.format(meta['chunk_size']))

            if self.context.is_remote:
                # For remote context we must create a resource provider
                self.rrp = RemoteResourceProvider(self.context.session, meta)
                # and create a remote per task temporary directory.
                if 'resources' in message['task'] or\
                   'resources_mapped' in message['task']:
                    await session.call('fs.mkdir', self.tempfs_dir.as_posix())

                if 'resources' in message['task']:
                    message['task']['resources'] += await self.rrp.upload(message['task']['resources'],
                                                                self.tempfs_dir)
                if 'resources_mapped' in message['task']:
                    if 'resources' not in message['task']:
                        message['task']['resources'] = []
                    message['task']['resources'] += await self.rrp.upload(message['task']['resources_mapped'],
                                        self.tempfs_dir)    

            self.task = self._serialize_task(message['task'])

            await session.subscribe(self.on_task_status_update,
                                    u'evt.comp.task.status')
            await session.subscribe(self.on_subtask_status_update,
                                    u'evt.comp.subtask.status')

            task_id, error = await session.call('comp.task.create', self.task)

            if error is not None:
                raise Exception(error)

            self.task_id = task_id

            asyncio.get_event_loop().create_task((self.collect_task(session)))

            return self.task_id
        elif message['type'] == 'VerifyResults':
            await session.call('comp.task.verify_subtask',
                               message['subtask_id'],
                               message['verdict'])
        else:
            raise NotImplementedError()

    def _serialize_task(self, task):
        if task['type'] in self.serializers:
            return self.serializers[task['type']].dump(task)
        else:
            return self.serializers['_Task'].dump(task) 
    async def on_task_status_update(self, task_id, op_class, op_value):
        # Store a tuple with all the update information
        if task_id == self.task_id:
            logging.info("{} (task_id): {}: {}".format(task_id, TaskOp(op_value), op_class))
            self.event_arr.append(
                (task_id, op_class, TaskOp(op_value))
            )

    async def on_subtask_status_update(self, task_id, subtask_id, op_value):
        # Store a tuple with all the update information
        if task_id == self.task_id:
            logging.info("{} (task_id): {}: {}".format(task_id, SubtaskOp(op_value), subtask_id))
            if SubtaskOp(op_value) == SubtaskOp.VERIFYING:
                self.context.response_q.sync_q.put({
                    'type': 'VerificationRequired',
                    'task_id': task_id,
                    'subtask_id': subtask_id,
                    'results': []
                })

    async def collect_task(self, session):
        # Active polling, not optimal but trivial
        related_evts = []

        while True:
            # Task API polling
            await asyncio.sleep(self.polling_interval)

            # Get task_id related evts from all events
            related_evts = list(filter(lambda evt: evt[0] == self.task_id, self.event_arr))
            self.clear_task_evts()
            for _, _, op in related_evts:
                if TaskOp.is_completed(op):
                    if op != TaskOp.FINISHED:
                        self.context.response_q.sync_q.put(RuntimeError(op))
                        return
                    else:
                        results = await session.call('comp.task.result', self.task_id)
                        if self.context.is_remote:
                            # Create results download directory
                            dest = os.path.join(self.task_id + '-output')
                            os.mkdir(dest)

                            # We overwrite actual results with downloaded results
                            # directory path
                            results = await self.rrp.download(
                                results,
                                dest
                            )
                            # After results are downloaded we free up remote resources
                            await self.context.session.call('comp.task.results_purge', self.task_id)
                            if self.task['resources']:
                                await self.context.session.call('fs.removetree', self.tempfs_dir.as_posix())
                        self.is_finished = True
                        self.context.response_q.sync_q.put({
                            'type': 'TaskResults',
                            'task_id': self.task_id,
                            'results': results
                        })
                        return

    def clear_task_evts(self):
        self.event_arr = list(filter(lambda evt: evt[0] != self.task_id, self.event_arr))
