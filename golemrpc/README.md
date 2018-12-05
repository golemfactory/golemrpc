# How to run locally

Set up two Golem nodes (1 requestor and 1 provider):


```sh
# First node listening on port 61000
python $GOLEM_DIR/golemapp.py --datadir=/home/$USER/datadir1 --password=node1 --accept-terms --rpc-address=localhost:61000
# Second node listening on port 61001
python $GOLEM_DIR/golemapp.py --datadir=/home/$USER/datadir2 --peer=localhost:40102 --rpc-address=localhost:61001
```

Start example `main.py`:

```sh
source venv/bin/activate
python main.py
```