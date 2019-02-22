import asyncio
import copy
import logging
import marshmallow
import os
from pathlib import PurePath
import uuid

from autobahn.asyncio.wamp import Session

from ..core_imports import TaskOp, SubtaskOp
from ..transfermanager import TransferManager

from ..schemas.tasks import GLambdaTaskSchema, TaskSchema
from ..remote_resources_provider import RemoteResourcesProvider


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
        rpc = self.context.rpc

        # FIXME create self.Create method
        if message['type'] == 'CreateTask':
            # An exception is thrown if something is wrong with
            # the task format

            meta = await rpc.call('fs.meta')
            # FIXME Is this serialized to string or some cbor/msgpack??
            if len(str(self.task)) > meta['chunk_size']:
                raise ValueError('serialized task exceeds maximum chunk_size {}\
                    consider using \'resources\' to transport bigger files'.format(meta['chunk_size']))

            if self.context.is_remote:
                self.rrp = RemoteResourcesProvider(self.tempfs_dir,
                                                  self.context.rpc,
                                                  meta,
                                                  TransferManager(self.context.rpc, meta))
                message['task']['resources'] = self.rrp.create(message['task'])

            self.task = self._serialize_task(message['task'])

            await rpc.subscribe(self.on_task_status_update,
                                    u'evt.comp.task.status')
            await rpc.subscribe(self.on_subtask_status_update,
                                    u'evt.comp.subtask.status')

            task_id, error = await rpc.call('comp.task.create', self.task)

            if error is not None:
                raise Exception(error)

            self.task_id = task_id

            asyncio.get_event_loop().create_task((self.collect_task(rpc)))

            self.context.response_q.sync_q.put({
                'type': 'TaskCreatedEvent',
                'task_id': task_id
            })

    def _serialize_task(self, task):
        if task['type'] in self.serializers:
            return self.serializers[task['type']].dump(task)
        else:
            return self.serializers['_Task'].dump(task) 

    async def on_task_status_update(self, task_id, op_class, op_value):
        if not task_id == self.task_id:
            return

        logging.info("{} (task_id): {}: {}".format(task_id, TaskOp(op_value), op_class))
        self.event_arr.append(
            (task_id, op_class, TaskOp(op_value))
        )

    async def on_subtask_status_update(self, task_id, subtask_id, op_value):
        pass

    async def collect_task(self, rpc):
        # Active polling, not optimal but trivial
        related_evts = []

        while True:
            # Task API polling
            await asyncio.sleep(self.polling_interval)

            # Get task_id related evts from all events
            related_evts = list(filter(lambda evt: evt[0] == self.task_id, self.event_arr))
            self.clear_task_evts()
            for _, _, op in related_evts:

                if not TaskOp.is_completed(op):
                    continue

                if op != TaskOp.FINISHED:
                    self.context.response_q.sync_q.put(RuntimeError(op))
                    return

                else:
                    results = await rpc.call('comp.task.result', self.task_id)
                    if self.context.is_remote:
                        # We overwrite actual results with downloaded results
                        # directory path
                        results = await self.rrp.download(
                            results,
                            os.path.join(self.task_id + '-output')
                        )
                        # Clear resources uploaded on task creation
                        await self.rrp.clear()
                        # After results are downloaded we free up remote resources
                        await self.context.rpc.call('comp.task.results_purge', self.task_id)
                    self.is_finished = True
                    self.context.response_q.sync_q.put({
                        'type': 'TaskResults',
                        'task_id': self.task_id,
                        'results': results
                    })
                    return

    def clear_task_evts(self):
        self.event_arr = list(filter(lambda evt: evt[0] != self.task_id, self.event_arr))


class UserVerifiedTaskMessageHandler(TaskMessageHandler):
    async def on_message(self, message):
        await super(UserVerifiedTaskMessageHandler, self).on_message(message)
        if message['type'] == 'VerifyResults':
            await self.context.rpc.call('comp.task.verify_subtask',
                                message['subtask_id'],
                                message['verdict'])

    async def on_subtask_status_update(self, task_id, subtask_id, op_value):
        if not task_id == self.task_id:
            return

        logging.info("{} (task_id): {}: {}".format(task_id, 
                                                   SubtaskOp(op_value),
                                                   subtask_id))
        if SubtaskOp(op_value) == SubtaskOp.VERIFYING:
            results = await self.context.rpc.call('comp.task.subtask_results',
                                                      task_id,
                                                      subtask_id)
            self.context.response_q.sync_q.put({
                'type': 'VerificationRequired',
                'task_id': task_id,
                'subtask_id': subtask_id,
                'results': await self.rrp.download(results,
                                                   os.path.join(subtask_id + '-output'))
            })