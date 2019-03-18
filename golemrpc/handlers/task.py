import asyncio
import logging
import os
import uuid
from pathlib import PurePath

import marshmallow

from ..core_imports import TaskOp, SubtaskOp
from ..remote_resources_provider import RemoteResourcesProvider
from ..schemas.tasks import GLambdaTaskSchema, TaskSchema
from ..transfermanager import TransferManager


class TaskMessageHandler(object):
    def __init__(self, context, polling_interval=0.5):
        self.context = context
        self.event_arr = []
        self.polling_interval = polling_interval
        self.task = None
        self.task_serialized = None
        self.task_id = None
        self.tempfs_dir = PurePath('temp_{}'.format(uuid.uuid1()))
        self.serializers = {
            'GLambda': GLambdaTaskSchema(unknown=marshmallow.INCLUDE),
            # Generic serializer
            '_Task': TaskSchema(unknown=marshmallow.INCLUDE)
        }

    async def on_message(self, message):
        rpc = self.context.rpc

        if message['type'] == 'CreateTask':
            self.task = message['task']

            self.task_serialized = self._serialize_task(message['task'])

            '''
            # NOTE Add support in Golem
            if len(str(self.task_serialized)) > meta['chunk_size']:
                raise ValueError('serialized task exceeds maximum chunk_size {}\
                    consider using \'resources\' to transport bigger \
                    files'.format(meta['chunk_size']))
            '''

            await rpc.subscribe(self.on_task_status_update,
                                u'evt.comp.task.status')
            await rpc.subscribe(self.on_subtask_status_update,
                                u'evt.comp.subtask.status')

            task_id, error = await rpc.call('comp.task.create',
                                            self.task_serialized)

            if error is not None:
                raise Exception(error)

            self.task_id = task_id

            asyncio.get_event_loop().create_task((self.collect_task(rpc)))

            self.context.response_q.sync_q.put({
                'type': 'TaskCreatedEvent',
                'task_id': task_id,
                'task': message['task']
            })

    def _serialize_task(self, task):
        if task['type'] in self.serializers:
            return self.serializers[task['type']].dump(task)
        else:
            return self.serializers['_Task'].dump(task)

    async def on_task_status_update(self, task_id, op_class, op_value):
        if not task_id == self.task_id:
            return

        logging.info(
            "{} (task_id): {}: {}".format(task_id, TaskOp(op_value), op_class))
        self.event_arr.append(
            (task_id, op_class, TaskOp(op_value))
        )

    async def on_subtask_status_update(self, task_id, subtask_id, op_value):
        pass

    async def collect_task(self, rpc):
        # Active polling, not optimal but trivial
        related_evts = []

        while True:
            await asyncio.sleep(self.polling_interval)

            # Get task_id related evts from all events
            related_evts = list(
                filter(lambda evt: evt[0] == self.task_id, self.event_arr))

            # Remove them from self.event_arr
            self.clear_task_evts()

            for _, _, op in related_evts:

                if not TaskOp.is_completed(op):
                    continue

                if op != TaskOp.FINISHED:
                    self.context.response_q.sync_q.put(RuntimeError(op))
                    return

                else:
                    state = await rpc.call('comp.task.state', self.task_id)
                    self.context.response_q.sync_q.put({
                        'type': 'TaskResults',
                        'task_id': self.task_id,
                        'results': state['outputs'],
                        'task': self.task
                    })
                    return

    def clear_task_evts(self):
        self.event_arr = list(
            filter(lambda evt: evt[0] != self.task_id, self.event_arr))


class RemoteTaskMessageHandler(TaskMessageHandler):
    async def on_message(self, message):
        rpc = self.context.rpc

        if message['type'] == 'CreateTask':
            self.task = message['task']

            meta = await rpc.call('fs.meta')
            self.rrp = RemoteResourcesProvider(self.tempfs_dir,
                                               self.context.rpc,
                                               meta,
                                               TransferManager(self.context.rpc,
                                                               meta)
                                               )
            message['task']['resources'] = await self.rrp.create(
                message['task'])

            self.task_serialized = self._serialize_task(message['task'])

            if len(str(self.task_serialized)) > meta['chunk_size']:
                raise ValueError('serialized task exceeds maximum chunk_size {}\
                    consider using \'resources\' to transport bigger \
                    files'.format(meta['chunk_size']))

            await rpc.subscribe(self.on_task_status_update,
                                u'evt.comp.task.status')
            await rpc.subscribe(self.on_subtask_status_update,
                                u'evt.comp.subtask.status')

            task_id, error = await rpc.call('comp.task.create',
                                            self.task_serialized)

            if error is not None:
                raise Exception(error)

            self.task_id = task_id

            asyncio.get_event_loop().create_task((self.collect_task(rpc)))

            self.context.response_q.sync_q.put({
                'type': 'TaskCreatedEvent',
                'task_id': task_id,
                'task': message['task']
            })

    async def collect_task(self, rpc):
        # Active polling, not optimal but trivial
        related_evts = []

        while True:
            await asyncio.sleep(self.polling_interval)

            # Get task_id related evts from all events
            related_evts = list(
                filter(lambda evt: evt[0] == self.task_id, self.event_arr))

            # Remove them from self.event_arr
            self.clear_task_evts()

            for _, _, op in related_evts:

                if not TaskOp.is_completed(op):
                    continue

                if op != TaskOp.FINISHED:
                    self.context.response_q.sync_q.put(RuntimeError(op))
                    return

                else:
                    results = await rpc.call('comp.task.result', self.task_id)
                    # We overwrite actual results (pointing to remote filesystem
                    # with downloaded results paths
                    results = await self.rrp.download(
                        results,
                        os.path.join(self.task_id + '-output')
                    )

                    # Clear resources uploaded on task creation
                    await self.rrp.clear()

                    # After results are downloaded we free up remote resources
                    await self.context.rpc.call('comp.task.results_purge',
                                                self.task_id)

                    self.context.response_q.sync_q.put({
                        'type': 'TaskResults',
                        'task_id': self.task_id,
                        'results': results,
                        'task': self.task
                    })
                    return


class UserVerifiedRemoteTaskMessageHandler(RemoteTaskMessageHandler):
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
                'task': self.task,
                'subtask_id': subtask_id,
                'results': await self.rrp.download(results,
                                                   os.path.join(
                                                       subtask_id + '-output'))
            })
