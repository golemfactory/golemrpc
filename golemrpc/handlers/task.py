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


class TaskRemoteFSDecorator(object):
    '''TaskRemoteFSMappingDecorator allows to recreate task's
    resources on remote side (remote Golem requestor). User
    has to specify `resources` key as usual for golem task dict.
    Those resources will be uploaded to a virtual filesystem on
    remote golem. Key `resources` will be modified to resemble
    remote paths.
    '''

    def __init__(self, taskmap_handler):
        self.taskmap_handler = taskmap_handler

    async def __call__(self, context, message):
        session = context.session
        task = message['task']
        # Meta contains information about remote `sys.platform`
        #  and max allowed chunk size for the file transfer.
        meta = await session.call('fs.meta')
        transfer_mgr = TransferManager(session, meta)

        # _syspath is a path to remote node's virtual filesystem root
        # directory. This will be later used to generate `_resources` in
        # task dict to resemble remote file system.
        _syspath = PurePath(await session.call('fs.getsyspath', ''))

        # Replace 'resources' f
        if 'resources' in task:
            # Original 'resources' will be replaced with _resources
            # pointing to remote host filesystem
            _resources = []

            # For each task we create a separate tmpdir on remote
            tempfs_dir = PurePath('temp_{}'.format(uuid.uuid1()))

            await session.call('fs.mkdir', tempfs_dir.as_posix())

            # Upload each resource to remote
            for r in task['resources']:
                r = PurePath(r)
                # Place resources on remote filesystem root directory
                # e.g. 'foo/bar/file.txt' -> '$tempfs_dir/file.txt'
                remote_path = tempfs_dir / r.name
                await transfer_mgr.upload(r.as_posix(), remote_path.as_posix())
                # For remote side to pick up resources during task requesting an
                # absolute path to resources has to be put in _resources, e.g.
                # $_syspath = /tmp
                # $tempfs_dir = tempfs1234
                # local resource = foo/bar/file.txt
                # _resource = /tmp/tempfs1234/file.txt
                _resources.append((_syspath / remote_path).as_posix())

            task['resources'] = _resources
            # Save tempfs_dir in task_dict for other decorators to re-use
            task['tempfs_dir'] = tempfs_dir.as_posix()

        # pass the modified task_dict to taskmap_handler for further processing
        response = await self.taskmap_handler(context, message)

        # Download task result to ${task_id}-output directory e.g.
        # if results are equal to ['foo.txt', 'bar.txt'] then resulting
        # directory structure will looks as follows:
        # .
        # `-- ${task_id}-output
        #      |-- foo.txt
        #      |-- bar.txt

        task_result_path = os.path.join(response['task_id'] + '-output')
        os.mkdir(task_result_path)

        download_futures = []
        for result in response['results']:
            dest = os.path.join(task_result_path,
                                os.path.basename(result))
            download_futures.append(transfer_mgr.download(result, dest))
        await asyncio.gather(*download_futures)

        # After results are downloaded we free up remote resources
        await session.call('comp.task.results_purge', response['task_id'])

        if 'tempfs_dir' in task:
            await session.call('fs.removetree', task['tempfs_dir'])

        response['results'] = [task_result_path]

        return response


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
    def __init__(self, next_handler):
        self.next_handler = next_handler

    async def __call__(self, context, message):
        session = context.session
        task = message['task']
        meta = await session.call('fs.meta')
        transfer_mgr = TransferManager(session, meta)

        # _syspath is a directory on remote where `fs` module
        # has opened it's virtual directory. It's necessary to construct
        # a task_dict with `resources` appropriate for remote host. Otherwise
        # there is no way of knowing where exactly remote host puts
        # it's resources.
        _syspath = PurePath(await session.call('fs.getsyspath', ''))

        if 'resources_mapped' in task:
            if not isinstance(task['resources_mapped'], dict):
                raise RuntimeError('resource_mapped must be a dict')

            # Those will be filled later based on what is created
            # from `resources_mapped`
            if 'resources' not in task:
                task['resources'] = []

            # tempfs_dir could be already created on remote and put into
            # task_dict by some other task_dict handling logic.
            # Same tempfs_dir must be used accross single task
            if 'tempfs_dir' in task:
                tempfs_dir = PurePath(task['tempfs_dir']) 
            else:
                tempfs_dir = PurePath('temp_{}'.format(uuid.uuid1()))
                await session.call('fs.mkdir', tempfs_dir.as_posix())

            for src, dest in task['resources_mapped'].items():

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
                            await session.call('fs.mkdir', (tempfs_dir / anchor).as_posix())
                    remote_path = tempfs_dir / dest
                    await transfer_mgr.upload(src.as_posix(), remote_path.as_posix())

                    if parents:
                        # If there is a directory structure defined in mapping
                        # then a resource path should point to it's last anchor e.g.
                        # 'dir1/dir2/foo` should yield `dir1`.
                        resources_dir_path = _syspath / tempfs_dir / parents[-1]
                    else:
                        resources_dir_path = _syspath / tempfs_dir / dest

                    task['resources'].append(resources_dir_path.as_posix())

                else:
                    remote_path = tempfs_dir / src.name
                    await transfer_mgr.upload(src.as_posix(), remote_path.as_posix())
                    task['resources'].append((_syspath / remote_path).as_posix())

        return await self.next_handler(context, message)


class TaskMessageHandler(object):
    def __init__(self, polling_interval=0.5):
        self.event_arr = []
        self.polling_interval = polling_interval
        self.task_id = None
        self.serializers = {
            'GLambda': GLambdaTaskSchema(unknown=marshmallow.INCLUDE),
            # Generic serializer
            '_Task': TaskSchema(unknown=marshmallow.INCLUDE)
        }

    async def __call__(self, context, message):
        session = context.session

        # An exception is thrown if something is wrong with
        # the task format
        task = self._serialize_task(message['task'])

        meta = await session.call('fs.meta')
        # FIXME Is this serialized to string or some cbor/msgpack??
        if len(str(task)) > meta['chunk_size']:
            raise ValueError('serialized task exceeds maximum chunk_size {}\
                 consider using \'resources\' to transport bigger files'.format(meta['chunk_size']))

        await session.subscribe(self.on_task_status_update,
                                u'evt.comp.task.status')
        await session.subscribe(self.on_subtask_status_update,
                                u'evt.comp.subtask.status')

        task_id, error = await session.call('comp.task.create', task)

        if error is not None:
            raise Exception(error)

        self.task_id = task_id

        return await self.collect_task(session)

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

    async def collect_task(self, session):
        # Active polling, not optimal but trivial
        related_evts = []

        while True:
            # Task API polling
            await asyncio.sleep(self.polling_interval)

            # Get task_id related evts from all events
            related_evts = list(filter(lambda evt: evt[0] == self.task_id, self.event_arr))
            for _, _, op in related_evts:
                if TaskOp.is_completed(op):
                    self.clear_task_evts()
                    if op != TaskOp.FINISHED:
                        raise RuntimeError(op)
                    else:
                        return {
                            'type': 'TaskResults',
                            'task_id': self.task_id,
                            'results': await session.call('comp.task.result', self.task_id)
                        }

    def clear_task_evts(self):
        self.event_arr = list(filter(lambda evt: evt[0] != self.task_id, self.event_arr))
