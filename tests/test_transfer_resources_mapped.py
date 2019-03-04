import json
import os
import pytest
import shutil

from utils import create_rpc_component

GLAMBDA_RESULT_FILE = 'result.json'


def test_empty_mapping():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        return True

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task
        }
    })

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_absolute_mapping_exception():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    def dummy_task(args):
        return True

    with pytest.raises(AssertionError):
        _ = rpc.post_wait({
            'type': 'CreateTask',
            'task': {
                'type': 'GLambda',
                'method': dummy_task,
                'resources_mapped': {'tmpfile': '/usr/bin/echo'}
            }
        })


def test_single_file_mapping():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources')
        if 'tmpfile' not in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {'tmpfile': ''}
        }
    })

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    os.remove('tmpfile')

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_file_mapping2():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources')
        if 'tmpfile' not in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {'tmpfile': None}
        }
    })

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    os.remove('tmpfile')

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_file_mapping_rename():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources')
        if 'tmpfile2' not in resources:
            return False

        if 'tmpfile' in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {'tmpfile': 'tmpfile2'}
        }
    })

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    os.remove('tmpfile')

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_file_mapping_rename_with_dir():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/foo')
        if 'tmpfile2' not in resources:
            return False

        if 'tmpfile' in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {'tmpfile': 'foo/tmpfile2'}
        }
    })

    os.remove('tmpfile')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_dir_mapping():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/foo')
        if 'tmpfile' not in resources:
            return False

        return True

    os.mkdir('foo')

    with open('foo/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {'foo': ''}
        }
    })

    shutil.rmtree('foo')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_dir_mapping_rename():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/bar')
        if 'tmpfile' not in resources:
            return False

        return True

    os.mkdir('foo')

    with open('foo/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {'foo': 'bar'}
        }
    })

    shutil.rmtree('foo')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_dir_mapping_rename_with_dir():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/bar')
        if 'tmpfile' not in resources:
            return False

        if 'foo2' not in resources:
            return False

        resources = os.listdir('/golem/resources/bar/foo2')

        if 'tmpfile' not in resources:
            return False

        return True

    os.mkdir('foo')
    os.mkdir('foo/foo2')

    with open('foo/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    with open('foo/foo2/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {'foo': 'bar'}
        }
    })

    shutil.rmtree('foo')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_file_and_dir_mapping():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/bar')
        if 'tmpfile' not in resources:
            return False

        if 'foo2' not in resources:
            return False

        resources = os.listdir('/golem/resources/bar/foo2')

        if 'tmpfile' not in resources:
            return False

        resources = os.listdir('/golem/resources')
        if 'bar' not in resources:
            return False

        if 'tmpfile2' not in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    os.mkdir('foo')
    os.mkdir('foo/foo2')

    with open('foo/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    with open('foo/foo2/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {
                'foo': 'bar',
                'tmpfile': 'tmpfile2'
            }
        }
    })

    shutil.rmtree('foo')
    os.remove('tmpfile')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_nested_file():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources')

        if 'tmpfile' not in resources:
            return False

        return True

    os.mkdir('foo')
    os.mkdir('foo/foo2')

    with open('foo/foo2/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {
                'foo/foo2/tmpfile': '',
            }
        }
    })

    shutil.rmtree('foo')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_file_nested_mapping():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/foo/bar')

        if 'tmpfile' not in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {
                'tmpfile': 'foo/bar/tmpfile',
            }
        }
    })

    os.remove('tmpfile')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_dir_nested_mapping():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/foo/baz')

        if 'tmpfile' not in resources:
            return False

        if 'bar' not in resources:
            return False

        resources = os.listdir('/golem/resources/foo/baz/bar')

        if 'tmpfile' not in resources:
            return False

        return True

    os.mkdir('foo')
    os.mkdir('foo/bar')

    with open('foo/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    with open('foo/bar/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {
                'foo': 'foo/baz',
            }
        }
    })

    shutil.rmtree('foo')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_overlaping_mapping():
    rpc = create_rpc_component()
    rpc.remote = True
    rpc.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/foo')

        if 'tmpfile' not in resources:
            return False

        if 'tmpfile2' not in resources:
            return False

        return True

    os.mkdir('foo')

    with open('foo/tmpfile', 'wb') as f:
        f.write(b'\xDA')

    with open('foo/tmpfile2', 'wb') as f:
        f.write(b'\xDA')

    _ = rpc.post_wait({
        'type': 'CreateTask',
        'task': {
            'type': 'GLambda',
            'method': dummy_task,
            'resources_mapped': {
                'foo/tmpfile': 'foo/tmpfile',
                'foo/tmpfile2': 'foo/tmpfile2',
            }
        }
    })

    shutil.rmtree('foo')

    results = rpc.poll(timeout=None)['results']
    result_directory = os.path.split(results[0])[0]

    assert set(os.path.basename(r) for r in results) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True
