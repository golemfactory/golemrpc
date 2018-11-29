from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

import asyncio
import cloudpickle
import txaio

from core_imports import TaskOp

class MultipleLambdaStrategy(object):
    def __init__(self, session):
        self.session = session
        # Events received from subscription to 'evt.comp.task.status'
        self.event_arr = []

    async def __call__(self, data):
        methods = data['methods']
        args = data['args']
        futures = [
            self.compute_task(self.create_task_data(m, a)) for
            m, a in zip(methods, args)
        ]

        create_results = await asyncio.gather(*futures)

        if any(error_message for _, error_message in create_results):
            # Some tasks failed to created, abort all
            futures = [
                self.session.call('comp.task.abort', task_id) for
                task_id, _ in create_results
            ]

            # Await for all aborts to complete
            await asyncio.gather(*futures)

            raise RuntimeError('Failed to create tasks: ' + str(create_results))

        # Subscribe for updates before sending create requests
        await self.session.subscribe(self.on_task_status_update,
            u'evt.comp.task.status')

        futures = [
            self.collect_task(task_id) for 
            task_id, error_message in create_results
        ]

        return await asyncio.gather(*futures)

    async def compute_task(self, task_data):
        return await self.session.call('comp.task.create', task_data)

    def create_task_data(self, method, args):
        method_obj = cloudpickle.dumps(method)
        args_obj = cloudpickle.dumps(args)
        return {
            'type': "Blender",
            'name': 'test task',
            'timeout': "0:10:00",
            "subtask_timeout": "0:09:50",
            "subtasks_count": 2,
            "bid": 1.0,
            "resources": ['/home/mplebanski/Projects/golem/apps/blender/benchmark/test_task/cube.blend'],
            "options": {
                "output_path": '/home/mplebanski/Documents',
                "format": "PNG",
                "resolution": [
                    320,
                    240
                ]
            }
        }

        return {
            'bid': 1.0,
            'subtask_timeout': '00:10:00',
            'subtasks_count': 1,
            'timeout': '00:10:00',
            'type': 'Callable',
            'extra_data': {
                'method': method_obj,
                'args': args_obj
            },
            'name': 'My task'
        }

    async def on_task_status_update(self, task_id, subtask_id, op_value):
        # Store a tuple with all the update information
        self.event_arr.append(
            (task_id, subtask_id, TaskOp(op_value))
        )

    async def collect_task(self, task_id):
        # Active polling, not optimal but trivial
        related_evts = []

        while True:
            await asyncio.sleep(0.5)

            # Get task_id related evts from all events
            related_evts = list(filter(lambda evt: evt[0] == task_id, self.event_arr))

            if any(TaskOp.is_completed(op) for _, _, op in related_evts):
                self.clear_task_evts(task_id)
                break

        state = await self.session.call('comp.task.state', task_id)
        return state['outputs']

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))


class GolemRPCClient(object):

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
            MultipleLambdaStrategy: MultipleLambdaStrategy
        }

        # Set up component.on_join using functional Component API
        # This is queue receiver side
        @self.component.on_join
        async def joined(session: Session, details: SessionDetails):
            data = await self.q_tx.get()
            # Create handling strategy based on data type
            strategy = self.strategies[data['type']](session)

            results = await strategy(data['app_data'])

            # Waiting for the other side to pick up the results
            await self.q_rx.put(results)

            # We must disconnect otherwise component future will not resolve
            await session.leave()

    async def run_task(self, data):
        # FIXME For now we enforce exclusive access for input side 
        # for both queues because there is no way to distinguish actors
        # (in other words who should receive particular results if
        # results come unordered)
        results = None

        await self.queue_lock.acquire()

        try:
            await self.q_tx.put(data)
            results = await self.q_rx.get()
        except Exception as e:
            print(e)
        finally:
            self.queue_lock.release()

        return results

    async def start(self):
        await asyncio.gather(
            txaio.as_future(self.component.start, self.loop)
        )
    
    async def stop(self):
        self.session.leave()    
