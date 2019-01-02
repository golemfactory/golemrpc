# Example run manual

Manual assumes `python3.6` and `pip3` are available.

## Installation 


1. Download and unpack `golemrpc` project from branch `threaded`:
```shell
https://github.com/golemfactory/golemrpc/archive/threaded.zip
```

2. Install project locally with `pip3`:

```shell
cd golemrpc
pip3 install -e .
```

Now `golemrpc` should appear in `pip3 list` results.

## Testing the example

1. Get `golemcli.tck` and `rpc_cert.pem` for your remote node.

2. Edit `examples/raspa.py` to use your `cli_secret` and `rpc_cert`

```
component = RPCComponent(
    host='aws_node_ip_address',
    cli_secret='path_to_your_local_cli_secret',
    rpc_cert='path_to_your_local_rpc_cert'
)
```

3. Run example raspa task:

```shell
python3.6 examples/raspa.py
```

Results will be printed to standard output. 
