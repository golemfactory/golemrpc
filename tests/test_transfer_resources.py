import asyncio
import json
import os
from pathlib import Path, PurePath
import shutil
import tempfile

from utils import create_controller

# TODO move to test framework

GLAMBDA_RESULT_FILE = 'result.txt'


def test_no_output():
    controller = create_controller()
    controller.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        pass

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results
    controller.stop()


def test_big_file_output():
    controller = create_controller()
    controller.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log', 'result.bin'])
    FILE_SIZE = 50*1024*1024
    TESTBYTE = b'\xDA'

    def test_task(args):
        with open('/golem/output/result.bin', 'wb') as f:
            # Could use os.truncate but result is platform dependent
            # if the resulting file is bigger than before truncation
            # which is the case here
            for _ in range(FILE_SIZE):
                f.write(TESTBYTE)

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results
    assert os.stat(
        os.path.join(result_directory, 'result.bin')
    ).st_size == FILE_SIZE
    controller.stop()


def test_task_result_output():
    controller = create_controller()
    controller.start()

    TESTSTRING = 'test'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    def test_task(args):
        return TESTSTRING

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1

    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        assert f.read() == json.dumps({'data': TESTSTRING})
    controller.stop()


def test_directory_output():
    controller = create_controller()
    controller.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log', 'testdir'])
    TESTSTRING = b'\xDA'

    def test_task(args):
        import os
        os.mkdir('/golem/output/testdir')
        with open('/golem/output/testdir/testfile', 'wb') as f:
            f.write(TESTSTRING)

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results
    files_in_testdir = os.listdir(os.path.join(result_directory, 'testdir'))
    assert len(files_in_testdir) == 1
    assert 'testfile' in files_in_testdir

    with open(os.path.join(result_directory, 'testdir', 'testfile'), 'rb') as f:
        assert f.read() == TESTSTRING
    controller.stop()


def test_directory_file_output():
    controller = create_controller()
    controller.start()

    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log', 'testdir', 'testfile_top'])
    TESTSTRING = b'\xDA'

    def test_task(args):
        import os
        os.mkdir('/golem/output/testdir')
        with open('/golem/output/testdir/testfile', 'wb') as f:
            f.write(TESTSTRING)
        with open('/golem/output/testfile_top', 'wb') as f:
            f.write(TESTSTRING)

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results
    files_in_testdir = os.listdir(os.path.join(result_directory, 'testdir'))
    assert len(files_in_testdir) == 1
    assert 'testfile' in files_in_testdir

    with open(os.path.join(result_directory, 'testdir', 'testfile'), 'rb') as f:
        assert f.read() == TESTSTRING
    controller.stop()


def test_file_resource():
    controller = create_controller()
    controller.start()

    testfile = 'testfile'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])
    TESTSTRING = b'\xDA'

    with open(testfile, 'wb') as f:
        f.write(TESTSTRING)

    def test_task(args):
        with open(os.path.join('/golem/resources/', testfile), 'rb') as f:
            if TESTSTRING != f.read():
                raise ValueError('TESTSTRING does not match')
        return True

    results = controller.map(
        methods=[test_task],
        args=[{}],
        resources=[os.path.abspath(testfile)]
    )

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True

    controller.stop()

def test_file_resource():
    controller = create_controller()
    controller.start()

    testfile = 'testfile'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])
    TESTSTRING = b'\xDA'

    with open(testfile, 'wb') as f:
        f.write(TESTSTRING)

    def test_task(args):
        with open(os.path.join('/golem/resources/', testfile), 'rb') as f:
            if TESTSTRING != f.read():
                raise ValueError('TESTSTRING does not match')
        return True

    results = controller.map(
        methods=[test_task],
        args=[{}],
        resources=[os.path.abspath(testfile)]
    )

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True

    controller.stop()


def test_directory_resource():
    controller = create_controller()
    controller.start()

    TESTSTRING = b'\xDA'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])

    tmpd = PurePath(tempfile.mkdtemp())
    tmpd_basename = tmpd.name
    os.mkdir(os.path.join(tmpd, 'subdir'))

    with open(os.path.join(tmpd, 'tmpfile'), 'wb') as f:
        f.write(TESTSTRING)

    with open(os.path.join(tmpd, 'subdir', 'subdir_tempfile'), 'wb') as f:
        f.write(TESTSTRING)

    def test_task(args):
        golem_res = Path('/golem/resources')
        golem_tmpd = golem_res / Path(tmpd_basename)
        tmpd_file = golem_tmpd / 'tmpfile'
        tmpd_subdir = golem_tmpd / 'subdir'
        tmpd_subdir_file = tmpd_subdir / 'subdir_tempfile'

        if not tmpd_file.is_file():
            raise AssertionError(str(tmpd_file) + ' is not a file')
        with open(tmpd_file, 'rb') as f:
            if not TESTSTRING == f.read():
                raise AssertionError(TESTSTRING + ' does not match ' + str(tmpd_file))

        if not tmpd_subdir.is_dir():
            raise AssertionError(tmpd_subdir + ' is not a directory')
        if not tmpd_subdir_file.is_file():
            raise AssertionError(tmpd_subdir_file + ' is not a file')

        with open(tmpd_subdir_file, 'rb') as f:
            if not TESTSTRING == f.read():
                raise AssertionError(TESTSTRING + ' doest not match ' + str(tmpd_subdir_file))

        return True

    results = controller.map(
        methods=[test_task],
        args=[{}],
        resources=[os.path.abspath(tmpd)]
    )

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True

    shutil.rmtree(tmpd)
    controller.stop()


def test_file_chunk_resource():
    controller = create_controller()
    controller.start()

    testfile = 'testfile'
    expected_results = set([GLAMBDA_RESULT_FILE, 'stdout.log', 'stderr.log'])
    TESTSTRING = b'\xDA'

    c = controller.rpc_component
    chunk_size = c.post({
        'type': 'rpc_call',
        'method_name': 'fs.meta',
        'args': []
    })['chunk_size']

    with open(testfile, 'wb') as f:
        for _ in range(chunk_size):
            f.write(TESTSTRING)

    def test_task(args):
        with open(os.path.join('/golem/resources/', testfile), 'rb') as f:
            content = f.read()
            if not len(content) == chunk_size:
                raise ValueError('Uploaded file size mismatch')
        return True

    results = controller.map(
        methods=[test_task],
        args=[{}],
        resources=[os.path.abspath(testfile)]
    )

    assert len(results) == 1
    result_directory = os.path.join(results[0], 'output')
    assert set(os.listdir(result_directory)) == expected_results

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        j = json.loads(f.read())
        assert 'data' in j
        assert j['data'] is True

    controller.stop()
