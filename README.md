# Requirements

- Golem (branch `glambda0.3^3c8f9d425debb0e72017e427f7dc8edbca099185`)

# Quickstart

## Install with virtualenv


```sh
git clone git@github.com:golemfactory/golemrpc.git &&\
cd golemrpc &&\
python3 -m venv venv &&\
source venv/bin/activate &&\
pip install --upgrade pip  &&\
pip install -e .
```

## Run

Set up two Golem nodes (1 requestor and 1 provider):

```sh
# First node listening on port 61000
python $GOLEM_DIR/golemapp.py --datadir=/home/$USER/datadir1 --password=node1 --accept-terms --rpc-address=localhost:61000
# Second node listening on port 61001 and pointing to first as it's peer
python $GOLEM_DIR/golemapp.py --datadir=/home/$USER/datadir2 --peer=localhost:40102 --rpc-address=localhost:61001
```

Go to `golemrpc/examples/` directory and run one of the examples:

```sh
source venv/bin/activate
cd golemrpc/examples
python raspa_task.py
```

# Compatibility matrix

| Golem/Thin Client        | 0.1           | 0.2         |
| -------------------------|:-------------:| -----------:|
| develop                  | NO            | YES (local) |
| glambda0.2               | YES           | NO          |
| glambda0.3               | NO            | YES         |

It is possible to submit `Blender` tasks against `Golem^develop` if used in non `remote` mode. The default option for RPC component is `remote=True`, if you want to test blender, simply change the argument to RPCComponent constructor. See `examples/blender_task_local.py`.
