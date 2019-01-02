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

2. Edit `examples/raspa_remote.py` to use appropriate `host`, `cli_secret` and `rpc_cert`:

```
component = RPCComponent(
    host='35.158.100.16',
    cli_secret='golemcli_aws.tck',
    rpc_cert='rpc_cert_aws.pem'
)
```

3. Run example raspa task:

```shell
python3.6 examples/raspa.py
```

Results will be printed to standard output. 
