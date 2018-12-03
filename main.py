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
            def raspa_task(args):
                import RASPA2
                import pybel 

                mol = pybel.readstring('cif', args['mol'])

                return RASPA2.get_helium_void_fraction(mol)

            import pybel 
            import os
            import random
            import pathlib

            cif_files = [
                filepath.absolute() for filepath in pathlib.Path('./cifs').glob('*.cif')
            ]

            filtered_files = cif_files[15:20]

            files_content_arr = [
                open(f, 'r').read() for f in filtered_files
            ]

            task = {
                'type': MultiLambdaTask,
                'app_data': {
                    'methods': [raspa_task for _ in files_content_arr],
                    'args_dicts': [
                        {'mol': mol} for mol in files_content_arr
                    ]
                }
            }


            result_files = await mycomponent.run_task(task)

            results = []
            for f in result_files:
                try:
                    with open(f[0], 'r') as res:
                        results.append(res.read())
                except Exception as e:
                    results.append(str(e))

            for f, result in zip(filtered_files, results):
                print(f'{f}: {result}')

        group = asyncio.gather(
            mycomponent.start(),
            producer()
        )

        loop.run_until_complete(group)
    except Exception as e:
        logging.exception('')
