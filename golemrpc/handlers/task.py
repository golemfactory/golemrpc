import asyncio
import logging
import datetime
import os
import uuid
from pathlib import PurePath

import marshmallow

from ..core_imports import TaskOp, SubtaskOp
from ..remote_resources_provider import RemoteResourcesProvider
from ..schemas.tasks import GLambdaTaskSchema, TaskSchema
from ..transfermanager import TransferManager

class Messages:
    task_created_evt = 'TaskCreatedEvent'
    create_task = 'CreateTask'
    task_results = 'TaskResults'
    task_app_data = 'TaskAppData'
    verification_request = 'VerificationRequest'
    verify_results = 'VerifyResults'


class TaskHandler(object):
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
        self.started_on = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(self.context.logger.level)

    def notify(self, msg_type, **kwargs):
        self.context.response_q.sync_q.put({
            'type': msg_type,
            **kwargs
        })

    async def on_message(self, message):
        rpc = self.context.rpc

        if message['type'] == Messages.create_task:
            self.task = message['task']

            self.task_serialized = self._serialize_task(message['task'])

            meta = await rpc.call('fs.meta')

            if len(str(self.task_serialized)) > meta['chunk_size']:
                raise ValueError('serialized task exceeds maximum chunk_size {}\
                    consider using \'resources\' to transport bigger \
                    files'.format(meta['chunk_size']))

            await self._subscribe_to_events()

            task_id, error = await rpc.call('comp.task.create',
                                            self.task_serialized)

            if error is not None:
                raise Exception(error)

            self.task_id = task_id
            self.started_on = datetime.datetime.now()
            self.logger.info('Started task %s', task_id)

            asyncio.get_event_loop().create_task((self.collect_task(rpc)))

            self.notify(
                Messages.task_created_evt,
                **{'task_id': task_id, 'task': message['task']}
            )

        elif message['type'] == Messages.verify_results:
            await self.verify_results(message)

    async def _subscribe_to_events(self):
        await self.context.rpc.subscribe(self.on_task_status_update,
                            u'evt.comp.task.status')
        await self.context.rpc.subscribe(self.on_subtask_status_update,
                            u'evt.comp.subtask.status')
        await self.context.rpc.subscribe(self.on_task_app_data,
                            u'evt.comp.task.app_data')

    def _serialize_task(self, task):
        if task['type'] in self.serializers:
            return self.serializers[task['type']].dump(task)
        else:
            return self.serializers['_Task'].dump(task)

    async def on_task_status_update(self, task_id, op_class, op_value):
        if not task_id == self.task_id:
            return

        self.logger.debug(
            "{} (task_id): {}".format(task_id, TaskOp(op_value)))
        self.event_arr.append(
            (task_id, op_class, TaskOp(op_value))
        )

    async def on_subtask_status_update(self, task_id, subtask_id, op_value):
        if not task_id == self.task_id:
            return

        self.logger.info(f'{task_id} (task_id): {SubtaskOp(op_value)}: {subtask_id}')

    def on_task_app_data(self, task_id, app_data):
        if self.task_id == task_id:
            self.notify(
                Messages.task_app_data,
                **{'task': self.task, 'task_id': self.task_id, 'app_data': app_data}
            )

    async def verify_results(self, message):
        await self.context.rpc.call('comp.task.verify_subtask',
                                    message['subtask_id'],
                                    message['verdict'])

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
                    self.logger.info('Finished task %s (took %s)', self.task_id,
                                     datetime.datetime.now() - self.started_on)
                    state = await rpc.call('comp.task.state', self.task_id)
                    self.notify(
                        Messages.task_results,
                        **{'task_id': self.task_id, 'results': state['outputs'], 'task': self.task}
                    )
                    return

    def clear_task_evts(self):
        self.event_arr = list(
            filter(lambda evt: evt[0] != self.task_id, self.event_arr))

class RemoteTaskHandler(TaskHandler):
    async def on_message(self, message):
        rpc = self.context.rpc

        if message['type'] == Messages.create_task:
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

            await self._subscribe_to_events()

            task_id, error = await rpc.call('comp.task.create',
                                            self.task_serialized)

            if error is not None:
                raise Exception(error)

            self.task_id = task_id
            self.started_on = datetime.datetime.now()
            self.logger.info('Started task %s', task_id)

            asyncio.get_event_loop().create_task((self.collect_task(rpc)))

            self.notify(
                Messages.task_created_evt,
                **{'task_id': task_id, 'task': message['task']}
            )

        elif message['type'] == Messages.verify_results:
            await self.verify_results(message)

    async def on_task_app_data(self, task_id, app_data):
        if app_data['type'] == Messages.verification_request:
            subtask_id = app_data['subtask_id']
            results = await self._download_subtask_results(
                task_id, 
                subtask_id
            )
            app_data['results'] = await self.rrp.download(
                results,
                os.path.join(subtask_id + '-output')
            )
        super().on_task_app_data(task_id, app_data)

    async def _download_subtask_results(self, task_id, subtask_id):
        return await self.context.rpc.call(
            'comp.task.subtask_results',
            task_id,
            subtask_id)

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

                    self.logger.info('Finished task %s (took %s)', self.task_id,
                                datetime.datetime.now() - self.started_on)

                    self.notify(
                        Messages.task_results,
                        **{'task_id': self.task_id, 'results': results, 'task': self.task}
                    )
                    return
