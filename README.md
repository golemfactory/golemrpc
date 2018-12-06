# Requirements

- Golem core running on `localhost:61000` (branch glambda^334cb9250e9d2d0c4a7467385e7ef6ca254de5b9). It's required because `glambda` app is not yet implemented in the develop branch.
- golemrpc lib (branch master^75eb5d75e07ca8e80078cbd44246e768a4632e60)

# Installation

Clone from github:

```sh
git clone git@github.com:golemfactory/raspa-poc.git &&\
cd raspa-poc &&\
python3 -m venv venv &&\
source venv/bin/activate &&\
pip install --upgrade pip  &&\
pip install -e .
```


# How to run locally

Set up two Golem nodes (1 requestor and 1 provider):

```sh
# First node listening on port 61000
python $GOLEM_DIR/golemapp.py --datadir=/home/$USER/datadir1 --password=node1 --accept-terms --rpc-address=localhost:61000
# Second node listening on port 61001
python $GOLEM_DIR/golemapp.py --datadir=/home/$USER/datadir2 --peer=localhost:40102 --rpc-address=localhost:61001
```

Go to `raspa-poc/examples/` directory and run one of the examples:

```sh
source venv/bin/activate
cd raspa-poc/examples
python raspa.py
```