# Overview 

Golemrpc is a python package allowing communication with a (remote) Golem node. Connection handling, golem task state handling, resources upload and results retrieval are handled automatically for the user. This package has been created mainly for RASPA2 use case, but it also works with basic blender rendering tasks (see examples). 

RASPA2 tasks are submitted to Golem in the form of Python functions and `args` dictionary, e.g.:

```python
def raspa_task(args):
    '''Task to compute provider side.
    It is possible to import RASPA2 package on provider side because
    this package is preinstalled in a docker environment we are about
    to use (dockerhub golemfactory/glambda:1.3).
    '''
    import RASPA2
    import pybel

    mol = pybel.readstring('cif', args['mol'])

    return RASPA2.get_helium_void_fraction(mol)
```

It is called RASPA2, however generic Python functions are equally acceptable. 

## Requirements

User must have access to a Golem node (branch `glambda0.3`) with a public IP address and ports forwarded (e.g. AWS hosted). By having access, we mean possessing SSL certificate and CLI secret files required to establish a connection. For typical Golem installation, these are stored in `$golem_datadir/crossbar` directory.

## Architecture

Golemrpc allows users to make task requests without having to install Golem client and take care of port forwarding, GNT purchase etc. Library handles user defined tasks by communicating with Golem over RPC (remote procedure call) interface. This Golem node will be requesting tasks to P2P network on user's behalf. Requesting node can be hosted by anyone, anywhere e.g. on AWS EC2 instance.

Golem node running locally, i.e., as localhost, is also supported, but by default, this library will handle input/output files transfers over TCP. To disable it and take advantage of sharing the filesystem with Golem node, use `remote` argument in `RPCComponent` class.

## Installation

Use package installer for Python3.6:

```sh
pip3 install golemrpc
```

# User guide

## Basic example

First set up a logging module::

```python
import logging
logging.basicConfig(level=logging.INFO)
```

Then create and start an RPCComponent:

```python
from golemrpc.rpccomponent import RPCComponent
rpc = RPCComponent(
    host='35.158.100.160',
    port=61000,
    cli_secret_filepath='golemcli_aws.tck',
    rpc_cert_filepath='rpc_cert_aws.pem'
)
rpc.start()
```

It will spawn a separate thread that will handle communication with Golem on `35.158.100.160:61000`. Now define a `dummy_task` function 
to compute on Golem provider's machine:

```python
def dummy_task(args):
    return 1 + args['b']
```

Create a golemrpc `CreateTask` message with task type `GLambda` (an abbreviation for Golem Lambda, a type of task that takes serialized Python function and dictionary as input and sends them to the provider for computation. For more information about messages and events see [this](https://github.com/golemfactory/golemrpc/blob/threaded/docs/messages.md)):

```python
message = {
    'type': 'CreateTask',
    'task': {
        'type': 'GLambda',
        'options': {
            'method': dummy_task,
            'args': {'b': 2},
        },
    }
}
```

Send it to RPCComponent:

```python
rpc.post(message)
```

Now poll the RPC message queue for new events. First expected event is `TaskCreatedEvent`:

```python
task_created_event = rpc.poll(timeout=None)
```

It contains `task_id`assigned to this particular task by the requesting Golem node. One can use it to keep track of tasks in case there are more than one being computed at a time. Second message coming from RPCComponent should be `TaskResults` containing filepaths to actual results:

```python
task_results = rpc.poll(timeout=None)
```

By default there are three files listed in `TaskResults` message: `result.json`, `stderr.log` and `stdout.log`. Result returned by `dummy_task` function is serialized to a `result.json` of form:

```json
{
    "data": 3,
}
```

If there are any errors in user supplied function the JSON object will contain `error` key:

```json
{
    "error": "Some error message"
}
```

Pick result file, load it and verify the results:

```python
import json

result_json_file = None

for f in task_results['results']:
    if f.endswith('result.json'):
        result_json_file = f
        break

with open(result_json_file, 'r') as f:
    result_json = json.load(f)
assert result_json['data'] == (1 + 2)
```

## Big input files

By default `CreateTask` message cannot exceed 0.5MB. One must use `resources` task's field instead function `args` to supply bigger file inputs. Files listed in `resources` will be laid out in `/golem/resources` directory which is accessible from user supplied function, e.g.:

```python
def echo_task(args):
    my_input = None
    with open('/golem/resources/my_input.txt') as f:
        my_input = f.read()
    return my_input
```

is valid if followed by message:

```python
message = {
    'type': 'CreateTask',
    'task': {
        'type': 'GLambda',
        'options': {
            'method': echo_task,
        },
        'resources': ['my_input.txt']
    }
}
```

## Custom output files

There is no size limit for `result.json` file although one might want to use format different than JSON. To get back results in custom format user has to write them to a file in `/golem/output` directory. Every file in this directory will be packaged and sent back to user if it's listed in `outputs` field of `CreateTask` [message](https://github.com/golemfactory/golemrpc/blob/threaded/docs/messages.md), e.g.: 

```python
def echo_task(args):
    with open('/golem/resources/my_input.txt', 'r') as fin,\
         open('/golem/output/my_output.txt', 'w') as fout:
        fout.write(fin.read())
```

will create `my_output.txt` result file and send it back to user if created by message:

```python
import os
message = {
    'type': 'CreateTask',
    'task': {
        'type': 'GLambda',
        'options': {
            'method': echo_task,
            'outputs': ['my_output.txt']
        },
        'resources': ['{cwd}/my_input.txt'.format(cwd=os.getcwd())]
    }
}
```

## Local Golem nodes setup

First of all, in main Golem repository `golemfactory/golem` branch `glambda0.3` required for `GLambda` tasks to work is not yet merged into develop. One has to install Golem from source using `glambda0.3` branch. See Golem instructions for [running from source](https://github.com/golemfactory/golem/wiki/Installation#running-from-the-source).

Further steps assume that user has successfully installed Golem from source, has `GOLEM_DIR` variable defined.

Set up two Golem nodes:

 ```sh
# Node listening on port 61000, requestor.
python $GOLEM_DIR/golemapp.py --datadir=$HOME/datadir1 --password=node1 --accept-terms --rpc-address=localhost:61000	
# Node listening on port 61001, provider.
python $GOLEM_DIR/golemapp.py --datadir=$HOME/datadir2 --password=node2 --accept-terms --rpc-address=localhost:61001 --peer=localhost:40102
```

Now, if 1st node acts as a requestor, one should use CLI secret and SSL cert from `$HOME/datadir1/crossbar/rpc_cert.pem` and `$HOME/datadir1/crossbar/secrets/golemcli.tck`.

## Other

For more information regarding task requesting see our [examples](https://github.com/golemfactory/golemrpc/tree/threaded/examples).
