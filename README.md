# Quickstart

Golemrpc is a python client that allows you to use reuqest tasks in Golem Network without installing Golem on your local machine.

Usually, one needs to run full Golem node in order to participate in and use Golem Network. Golemrpc allows you to connect to specified Golem node that operates on your behalf in Golem Network. This way you can request your tasks and the remote Golem node handles networking and protocol. It even handles payments so you do not need to have any ETH and/or GNT. You only need to provide a script that connects to the remote Golem node and requests tasks - see our `examples`.

First of all, you need to know your remote Golem node. Contact the Golem node's administrator and obtain
1. IP address and port,
2. node's certificate that authenticates it, the `.pem` file,
3. access secret that authenticates you, the `.tck` file.

Optionally, you can run your own local Golem node. Aforementioned files can be found under paths: `$datadir/crossbar/rpc_cert.pem` and `$datadir/crossbar/secrets/golemcli.tck`.

System requirements:
1. [*Python3.6*](https://www.python.org/downloads/release/python-360/) installed.

Before running examples, perform a one time installation:

```sh
pip3 install golemrpc
```

Windows installation is a bit more complicated because one of our library's dependencies is not precompiled for this OS and `pip3` will try to compile it during installation. To successfully proceed with compilation one has to install VisualStudio with it's libraries. See our [VisualStudio installation manual](https://docs.golem.network/#/Products/Brass-Beta/Installation?id=visual-studio).

Take one of our examples: `examples/dummy_task_on_aws.py` or `examples/raspa_task_on_aws.py`. Copy the example script, `.pem` file and `.tck` file to a working directory.
If you want to use raspa, you also need to copy `examples/raspa_data` to the working directory. If you want to use dummy task, you need to create `my_input.txt` file in your home directory and write some human readable text as test data (to know why simply examine source code of the examples).
Now edit the script and update the connection config:

```python
rpc = RPCComponent(
    host='35.158.100.160',
    port=61000,
    cli_secret_filepath='golemcli_aws.tck',
    rpc_cert_filepath='rpc_cert_aws.pem'
)
```

Now you can run the script:

```sh
python3 your_example.py
```

After a while, you will see an output: a JSON object containing information on where to find the results (paths) and metadata of the submitted task.

### Complete script:

```sh
pip3 install golemrpc
git clone https://github.com/golemfactory/golemrpc.git
cd golemrpc/examples
# Edit the example if needed.
python3.6 raspa_task.py
```

# Overview

Golemrpc is a python package allowing communication with a (remote) Golem node. Connection handling, golem task state handling, resources upload and results retrieval are handled automatically for the user. This package has been created mainly for RASPA2 use case. Environment used for this Golem app has only few python packages installed.

RASPA2 tasks are submitted to Golem in the form of Python functions and `args` dictionary, e.g.:

```python
def raspa_task(args):
    '''Task to compute provider side.
    It is possible to import RASPA2 package on provider side because
    this package is preinstalled in a docker environment we are about
    to use (dockerhub golemfactory/glambda:1.5).
    '''
    import RASPA2
    import pybel

    mol = pybel.readstring('cif', args['mol'])

    return RASPA2.get_helium_void_fraction(mol)
```

It is called RASPA2, however generic Python functions are equally acceptable.

## Requirements

User must have access to a Golem node (`v0.20+`) with a public IP address and ports forwarded (e.g. AWS hosted). By having access, we mean possessing SSL certificate and CLI secret files required to establish a connection. For typical Golem installation, these are stored in `$golem_datadir/crossbar` directory.

## Architecture

Golemrpc allows users to make task requests without having to install Golem client and take care of port forwarding, GNT purchase etc. Library handles user defined tasks by communicating with Golem over RPC (remote procedure call) interface. This Golem node will be requesting tasks to P2P network on user's behalf. Requesting node can be hosted by anyone, anywhere, etc., for instance, on the AWS EC2 instance.

Golem node running locally, i.e., as localhost, is also supported, but by default, this library will handle input/output files transfers over TCP. To disable it and take advantage of sharing the filesystem with Golem node, use `remote` argument in `RPCComponent` class.

## Installation

Use package installer for Python3.6:

```sh
pip3 install golemrpc
```

# User guide

## Basic example

First set up a logging module:

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

Create a golemrpc `CreateTask` message with task type `GLambda` (an abbreviation for Golem Lambda, a type of task that takes serialized Python function and dictionary as input and sends them to the provider for computation. For more information about messages and events see [this](https://github.com/golemfactory/golemrpc/blob/master/docs/messages.md)):

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

By default, `CreateTask` message cannot exceed 0.5MB. One must use `resources` task's field instead of function `args` in order to supply bigger file inputs. Files listed in `resources` will be saved in `/golem/resources` directory (with the path structure preserved) which is accessible from the user supplied function, e.g.:

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

There is no size limit for `result.json` file although one might want to use format different than JSON. To get back the results in a custom format, you have to write them to a file in `/golem/output` directory. Every file in this directory will be packed and sent back to you if it is listed in `outputs` field of `CreateTask` [message](https://github.com/golemfactory/golemrpc/blob/master/docs/messages.md), e.g.:

```python
def echo_task(args):
    with open('/golem/resources/my_input.txt', 'r') as fin,\
         open('/golem/output/my_output.txt', 'w') as fout:
        fout.write(fin.read())
```

will create `my_output.txt` result file and send it back to the user when created by message:

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

One has to install Golem from source using `b0.20` branch. See Golem instructions for [running from source](https://github.com/golemfactory/golem/wiki/Installation#running-from-the-source).

Further steps assume that user has successfully installed Golem from source, and have `GOLEM_DIR` environment variable defined.

Set up two Golem nodes:

 ```sh
# Node listening on port 61000, requestor.
python $GOLEM_DIR/golemapp.py --datadir=$HOME/datadir1 --password=node1 --accept-terms --rpc-address=localhost:61000
# Node listening on port 61001, provider.
python $GOLEM_DIR/golemapp.py --datadir=$HOME/datadir2 --password=node2 --accept-terms --rpc-address=localhost:61001 --peer=localhost:40102
```

Now, if first node acts as a requestor, one should use CLI secret and SSL cert from `$HOME/datadir1/crossbar/rpc_cert.pem` and `$HOME/datadir1/crossbar/secrets/golemcli.tck`.

## Other

For more information regarding task requesting see our [examples](https://github.com/golemfactory/golemrpc/tree/master/examples).
