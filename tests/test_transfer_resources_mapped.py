import json
import os
import pytest
import shutil

from golemrpc.helpers import TaskMapFormatter

from utils import create_rpc_component as create_component

GLAMBDA_RESULT_FILE = 'result.txt'


def test_empty_mapping():
    component = create_component()
    component.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        return True

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={}
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_absolute_mapping_exception():
    component = create_component()
    component.start()

    def dummy_task(args):
        return True

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={'tmpfile': '/usr/bin/echo'}
    )

    with pytest.raises(AssertionError):
        results = component.post_wait({
            'type': 'map',
            't_dicts': formatter.format()
        })


def test_single_file_mapping():
    component = create_component()
    component.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources')
        if 'tmpfile' not in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'tmpfile': ''
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    os.remove('tmpfile')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_file_mapping2():
    component = create_component()
    component.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources')
        if 'tmpfile' not in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'tmpfile': None
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    os.remove('tmpfile')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_file_mapping_rename():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'tmpfile': 'tmpfile2'
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    os.remove('tmpfile')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_file_mapping_rename_with_dir():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'tmpfile': 'foo/tmpfile2'
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    os.remove('tmpfile')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_dir_mapping():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'foo': ''
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    shutil.rmtree('foo')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_dir_mapping_rename():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'foo': 'bar'
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    shutil.rmtree('foo')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_single_dir_mapping_rename_with_dir():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'foo': 'bar'
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    shutil.rmtree('foo')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_file_and_dir_mapping():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'foo': 'bar',
            'tmpfile': 'tmpfile2'
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    shutil.rmtree('foo')
    os.remove('tmpfile')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_nested_file():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'foo/foo2/tmpfile': ''
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    shutil.rmtree('foo')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_file_nested_mapping():
    component = create_component()
    component.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def dummy_task(args):
        import os

        resources = os.listdir('/golem/resources/foo/bar')

        if 'tmpfile' not in resources:
            return False

        return True

    with open('tmpfile', 'wb') as f:
        f.write(b'\xDA')

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'tmpfile': 'foo/bar/tmpfile'
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    os.remove('tmpfile')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_dir_nested_mapping():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'foo': 'foo/baz'
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    shutil.rmtree('foo')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True


def test_overlaping_mapping():
    component = create_component()
    component.start()

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

    formatter = TaskMapFormatter(
        methods=[dummy_task],
        args=[{}],
        resources_mapped={
            'foo/tmpfile': 'foo/tmpfile',
            'foo/tmpfile2': 'foo/tmpfile2'
            }
    )

    results = component.post_wait({
        'type': 'map',
        't_dicts': formatter.format()
    })

    shutil.rmtree('foo')

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True

