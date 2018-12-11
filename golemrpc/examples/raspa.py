import asyncio
import logging
from pathlib import Path

from golemrpc.helpers import get_golem_datadir
from golemrpc.helpers import LambdaTaskFormatter, MultiLambdaTaskFormatter
from golemrpc.taskrunner import GolemTaskRunner

loop = asyncio.get_event_loop()

# Task to compute on provider side
def raspa_task(args):
    import RASPA2
    import pybel

    mol = pybel.readstring('cif', args['mol'])

    return RASPA2.get_helium_void_fraction(mol)

# RASPA specific code for loading molecule structure files

cif_files = [
    filepath.absolute() for filepath in pathlib.Path('./cifs').glob('*.cif')
]

filtered_files = cif_files[18:20]

files_content_arr = [
    open(f, 'r').read() for f in filtered_files
]

# Formatting methods and args for golem rpc client
formatter = MultiLambdaTaskFormatter(
    methods=[raspa_task for _ in files_content_arr],
    args=[{'mol': mol} for mol in files_content_arr],
)

task = formatter.format()

datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

client = GolemTaskRunner(loop, 
    cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)

fut = client.run(task)
results = loop.run_until_complete(fut)

print(results)
