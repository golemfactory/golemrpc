# Example run manual

Manual assumes `python3.6` and `pip3` are available. `python3.7` does NOT work for now. Contact us if you really need it. 

## Installation 


1. Download and unpack `golemrpc` project from branch `threaded` https://github.com/golemfactory/golemrpc/archive/threaded.zip

2. Install project locally with `pip3`:

```shell
cd golemrpc-threaded
pip3 install -e .
```

Now `golemrpc` should appear in `pip3 list` results.

## Testing the example

1. Get `golemcli.tck` and `rpc_cert.pem` for your remote node (contact us for cloud hosted golem requestor credentials).

2. Edit `examples/raspa_remote.py` to use appropriate `host`, `cli_secret` and `rpc_cert`:

```
component = RPCComponent(
    host='35.158.100.160',
    cli_secret='golemcli_aws.tck',
    rpc_cert='rpc_cert_aws.pem'
)
```

3. Run example raspa task:

```shell
cd examples
python3.6 raspa_remote.py
```

Results will be printed to standard output. 
