import asyncio
import logging

from base import create_component
from client import GolemRPCClient
from lambdatask import LambdaTask
from multilambdatask import MultiLambdaTask
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

            task = {
                'type': MultiLambdaTask,
                'app_data': {
                    'methods': [
                        lambda args: 'a',
                        lambda args: 'b',
                        lambda args: 'c',
                        lambda args: 'd',
                        lambda args: 'e',
                        lambda args: 'f',
                    ],
                    'args_dicts': [
                        {},
                        {},
                        {},
                        {},
                        {},
                        {}
                    ]
                }
            }


            result_files = await mycomponent.run_task(task)

            results = []
            for f in result_files:
                with open(f[0], 'r') as res:
                    results.append(res.read())

            print(results)

            assert results[0] == 'a'
            assert results[1] == 'b'
            assert results[2] == 'c'


        group = asyncio.gather(
            mycomponent.start(),
            producer()
        )

        loop.run_until_complete(group)
    except Exception as e:
        logging.exception('')
