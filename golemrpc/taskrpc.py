from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

import asyncio
import txaio

from .core_imports import TaskOp


class GolemTaskRPC(object):

    def __init__(self, loop, component):
        self.loop = loop
        self.component = component

        # Using queues for passing input and retrieving results
        # is enforced by autobahn Component API. We must wait for on_join
        # and session establishment before making any calls
        self.q_tx = asyncio.Queue()
        self.q_rx = asyncio.Queue()
        self.queue_lock = asyncio.Lock()
        self.session = None

        self.strategies = {
            BaseTask: BaseTask,
            MultiTask: MultiTask
        }

        # Set up component.on_join using functional Component API
        # This is queue receiver side
        @self.component.on_join
        async def joined(session: Session, details: SessionDetails):
            data = await self.q_tx.get()
            # Create handling strategy based on data type
            if type(data) == list:
                strategy = self.strategies[MultiTask](session)
            else:
                strategy = self.strategies[BaseTask](session) 
            try: 
                results = await strategy(data)
            except BaseException as e:
                results = e

            # Waiting for the other side to pick up the results
            await self.q_rx.put(results)

            # We must disconnect otherwise component future will not resolve
            await session.leave()

    async def run(self, data):
        # FIXME For now we enforce exclusive access for input side 
        # for both queues because there is no way to distinguish actors
        # (in other words who should receive particular results if
        # results come unordered)
        results = None

        await self.queue_lock.acquire()

        try:
            await self.q_tx.put(data)
            results = await self.q_rx.get()

            # This is a hack to forward an exception coming from result queue
            if isinstance(results, BaseException):
                raise results

        except BaseException as e:
            self.queue_lock.release()
            raise e

        return results

    async def start(self):
        await asyncio.gather(
            txaio.as_future(self.component.start, self.loop)
        )
    
    async def stop(self):
        self.session.leave()    


class BaseTask(object):
    def __init__(self, session):
        self.session = session
        # Events received from subscription to 'evt.comp.task.status'
        self.event_arr = []
        self.subscribed = False

    async def __call__(self, t_dict):
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

    async def on_task_status_update(self, task_id, subtask_id, op_value):
        # Store a tuple with all the update information
        self.event_arr.append(
            (task_id, subtask_id, TaskOp(op_value))
        )

    async def collect_task(self, task_id):
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

        return  await self.session.call('comp.task.result', task_id)

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))


class MultiTask(BaseTask):
    async def __call__(self, t_dicts):
        futures = [
            super(MultiTask, self).__call__(t_dict) for
            t_dict in t_dicts
        ]
        return await asyncio.gather(*futures)