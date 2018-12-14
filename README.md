# Requirements

- Golem core running on `localhost:61000` (branch `glambda^1c5af343f1c5eb6e18a61bfdb2d8a4f82f3b21fe`). It's required because `glambda` app is not yet implemented in the develop branch.
- golemrpc lib 

# Installation

```sh
git clone git@github.com:golemfactory/golemrpc.git &&\
cd golemrpc &&\
python3 -m venv venv &&\
source venv/bin/activate &&\
pip install --upgrade pip  &&\
pip install -e .
```


# How to run locally

Go to your local golem repository and set up two Golem nodes (1 requestor and 1 provider):

```sh
# First node listening on port 61000
python $GOLEM_DIR/golemapp.py --datadir=/home/$USER/datadir1 --password=node1 --accept-terms --rpc-address=localhost:61000
# Second node listening on port 61001
python $GOLEM_DIR/golemapp.py --datadir=/home/$USER/datadir2 --peer=localhost:40102 --rpc-address=localhost:61001
```

Go to `golemrpc/examples/` directory and run one of the examples:

```sh
source venv/bin/activate
cd golemrpc/examples
python raspa.py
```
