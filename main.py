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

            args = {
                'val1': 10,
                'val2': 20
            }

            '''
            task = {
                'type': MultiLambdaTask,
                'app_data': {
                    'methods': [f],
                    'args_dicts': [args]
                }
            }
            '''

            task = {
                'type': LambdaTask,
                'app_data': {
                    'method': f,
                    'args_dict': args
                }
            }


            result_files = await mycomponent.run_task(task)

            results = []
            for f in result_files:
                with open(f, 'r') as res:
                    results.append(res.read())

            print(results)


        group = asyncio.gather(
            mycomponent.start(),
            producer()
        )

        loop.run_until_complete(group)
    except Exception as e:
        logging.exception('')
