from autobahn.asyncio.wamp import Session
from autobahn.wamp.types import SessionDetails

import asyncio
import txaio

from .core_imports import TaskOp
from .task import BaseTask
from .multitask import MultiTask


class GolemRPCComponent(object):

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
            results = await strategy(data)

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
