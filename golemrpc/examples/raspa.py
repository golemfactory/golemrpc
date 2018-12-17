from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

# Task to compute on provider side
def raspa_task(args):
    import RASPA2
    import pybel

    mol = pybel.readstring('cif', args['mol'])

    return RASPA2.get_helium_void_fraction(mol)

# RASPA specific code for loading molecule structure files

cif_files = [
    filepath.absolute() for filepath in Path('./cifs').glob('*.cif')
]

filtered_files = cif_files[18:20]

files_content_arr = [
    open(f, 'r').read() for f in filtered_files
]


datadir = '{home}/.local/share/golem/default/rinkeby'.format(home=Path.home())

c = RPCComponent(
    cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
    rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
)
c.start()

results = c.map(
    methods=[raspa_task for _ in files_content_arr],
    args=[{'mol': mol} for mol in files_content_arr]
)

print(results)

c.stop()
