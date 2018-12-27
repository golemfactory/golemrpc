# User manual

Every example requires user to provide CLI secret and RPC certificate for remote Golem access. These can be found in `$DATADIR/crossbar/rpc_cert.pem` and `$DATADIR/crossbar/secrets/golemcli.tck`.

Examples search for them in golem default installation directory, if this is not the case one must adjust them manually (provide correct paths in variables `cli_secret` and `rpc_cert`).
