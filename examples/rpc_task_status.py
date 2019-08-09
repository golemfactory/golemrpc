import logging
from pathlib import Path

from golemrpc.rpccomponent import RPCComponent

logging.basicConfig(level=logging.INFO)

# Golem default installation directory is where we obtain cli_secret_filepath and rpc_cert_filepath
# required for establishing connection with remote Golem.
datadir = '{home}/Projects/golem/node_A/rinkeby'.format(home=Path.home())

# cli_secret_filepath and rpc_cert_filepath paths specified below are default for typical Golem installation.
rpc = RPCComponent(
    cli_secret_filepath='{datadir}/crossbar/secrets/golemcli.tck'.format(
        datadir=datadir),
    rpc_cert_filepath='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir))

# Here a separate thread for RPC is created.
# Now user can send messages to the RPC Component to interact with
# remote Golem node.
rpc.start()

rpc.post({
    'type': 'RPCCall',
    'method_name': 'comp.tasks.stats',
    'args': []
})

result = rpc.poll(timeout=None)
print(result)