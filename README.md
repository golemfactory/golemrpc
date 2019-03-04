# Requirements

- Golem node (branch `glambda0.2^b78b8f03983f9708636476987d82736313b6e7f5`)
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
python raspa_task.py
```

# Compatibility matrix

| Golem/Thin Client        | 0.1           | 0.2  |
| -------------------------|:-------------:| ----:|
| develop                  | NO            | NO   |
| glambda0.2               | YES           | NO   |
| refactor_messages        | NO            | YES  |

A way to upload files to Golem is required for thin client to work. This is not planned for `develop` branch at the time of writing this.
