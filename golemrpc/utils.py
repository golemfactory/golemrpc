import ssl

from autobahn.asyncio.component import Component


def create_component(rpc_cert_filepath=None, cli_secret_filepath=None,
                     host='localhost', port=61000):
    # Mismatch golem.local - localhost
    ssl.match_hostname = lambda cert, hostname: True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.load_verify_locations(rpc_cert_filepath)

    with open(cli_secret_filepath, 'rb') as secretf:
        wampcra_secret = secretf.read()

    component = Component(
        transports=[
            {
                "type": "websocket",
                "url": "wss://{host}:{port}".format(host=host, port=port),
                "max_retries": 0,
                "endpoint": {
                    "host": host,
                    "type": "tcp",
                    "port": port,
                    "tls": context
                },
                "options": {
                    "open_handshake_timeout": 3,
                }
            }
        ],
        authentication={
            u"wampcra": {
                u'authid': 'golemcli',
                u'secret': wampcra_secret
            }
        },
        realm=u"golem",
    )
    return component
