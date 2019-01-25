from pathlib import Path

from golemrpc.controller import RPCController
from golemrpc.rpccomponent import RPCComponent

datadir = '{home}/Projects/golem/node_A/rinkeby'.format(home=Path.home())


def create_rpc_component():
    return RPCComponent(
        cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
        rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
    )


def create_controller():
    return RPCController(
        create_rpc_component()
    )
