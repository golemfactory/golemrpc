import asyncio
import logging

from base import create_component
from client import GolemRPCClient, MultipleLambdaStrategy

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()

        # Get default WAMP component 
        component = create_component(
            datadir='/home/mplebanski/Projects/golem/node_A/rinkeby'
        )

        # Wrap WAMP component to support task delegation
        mycomponent = GolemRPCClient(loop, component)

        async def producer():
            def f(args):
                return args['val1'] + args['val2']

            args = {
                'val1': 10,
                'val2': 20
            }

            task = {
                'type': MultipleLambdaStrategy,
                'app_data': {
                    'methods': [
                        f
                    ],
                    'args': [
                        args
                    ]
                }
            }

            results = await mycomponent.run_task(task)
            print(results)

        group = asyncio.gather(
            mycomponent.start(),
            producer()
        )

        loop.run_until_complete(group)
    except Exception as e:
        logging.exception('')
