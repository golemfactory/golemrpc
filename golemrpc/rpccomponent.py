import asyncio 
import queue
import threading
import txaio

from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

from .core_imports import TaskOp
from .helpers import MultiLambdaTaskFormatter
from .utils import create_component


class RPCComponent(threading.Thread):
    def __init__(self, cli_secret=None, rpc_cert=None, host='localhost', port=61000):
        self.cli_secret = cli_secret
        self.rpc_cert = rpc_cert
        self.host = host
        self.port = port
        # Cross thread communication queue
        self.lock = threading.Lock()
        self.call_q = queue.Queue()
        self.response_q = queue.Queue()
        self.event_q = queue.Queue(maxsize=16)
        self.session = None
        self.handlers = {
            'rpc_call': SingleRPCCallHandler(),
            'map': TaskMapHandler(),
            'exit': lambda session: session.leave
        }
        threading.Thread.__init__(self)

    def evaluate_sync(self, obj):
        # FIXME For now we enforce exclusive access for input side 
        # for both queues because there is no way to distinguish actors
        # (in other words who should receive particular results if
        # results come unordered)
        self.lock.acquire()

        self.call_q.put(obj)
        results = self.response_q.get()

        self.lock.release()

        return results

    def run(self):
        component = create_component(
            cli_secret=self.cli_secret,
            rpc_cert=self.rpc_cert,
            host=self.host,
            port=self.port
        )
        loop = asyncio.new_event_loop()

        txaio.config.loop = loop
        asyncio.set_event_loop(loop)

        @component.on_join
        async def joined(session: Session, details: SessionDetails):
            self.session = session
            while True:
                try:
                    obj = self.call_q.get(block=False)
                    # Handle depending on type in
                    result = await self.handlers[obj['type']](self.session, obj)
                except queue.Empty as e:
                    await asyncio.sleep(1.0)
                else:
                    self.response_q.put(result)

        fut =  asyncio.gather(
            txaio.as_future(component.start, loop)
        )
        loop.run_until_complete(fut)

    def stop(self):
        return self.evaluate_sync({
            'type': 'exit'
        })

    # FIXME: Later move it to composer class
    def map(self, methods=None, args=None):
        # Formatting methods and args for golem rpc client
        formatter = MultiLambdaTaskFormatter(
            methods=methods,
            args=args
        )
        return self.evaluate_sync({
            'type': 'map',
            't_dicts': formatter.format()
        })

class SingleRPCCallHandler(object):
    async def __call__(self, session, args_dict):
        method_name = args_dict['method_name']
        args = args_dict['args']
        return await session.call(method_name, *args)


class TaskMapHandler(object):
    def __init__(self):
        self.event_arr = []

    async def __call__(self, session, obj):
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
            await asyncio.sleep(0.5)

            # Get task_id related evts from all events
            related_evts = list(filter(lambda evt: evt[0] == task_id, self.event_arr))

            if any(TaskOp.is_completed(op) for _, _, op in related_evts):
                self.clear_task_evts(task_id)
                break

        return  await session.call('comp.task.result', task_id)

    def clear_task_evts(self, task_id):
        self.event_arr = list(filter(lambda evt: evt[0] != task_id, self.event_arr))
