import asyncio
import os
from pathlib import Path

from golemrpc.controller import RPCController
from golemrpc.rpccomponent import RPCComponent

GLAMBDA_RESULT_FILE = 'results.txt'

async def test_no_output(controller):
    def test_task(args):
        pass
    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    # There should be only a single result array for a single task
    assert len(results) == 1

    result_directory = results[0]
    result_files = os.listdir(result_directory)

    assert len(result_files) == 1
    print(result_files)
    assert result_files[0] == GLAMBDA_RESULT_FILE

async def test_big_file_output(controller):
    FILE_SIZE=50*1024*1024
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
    # There should be only a single result array for a single task
    assert len(results) == 1

    result_directory = results[0]
    result_files = os.listdir(result_directory)

    assert len(result_files) == 2
    assert GLAMBDA_RESULT_FILE in result_files
    assert 'result.bin' in result_files
    assert os.stat(
        os.path.join(result_directory, 'result.bin')
    ).st_size == FILE_SIZE

async def test_task_result_output(controller):
    def test_task(args):
        return 'test'

    results = controller.map(
        methods=[test_task],
        args=[{}]
    )
    # There should be only a single result array for a single task
    assert len(results) == 1

    result_directory = results[0]
    result_files = os.listdir(result_directory)

    assert len(result_files) == 1
    assert GLAMBDA_RESULT_FILE in result_files

    with open(os.path.join(result_directory, GLAMBDA_RESULT_FILE), 'r') as f:
        assert f.read() == 'test'

async def test_directory_output(controller):
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
    # There should be only a single result array for a single task
    assert len(results) == 1

    result_directory = results[0]
    result_files = os.listdir(result_directory)

    assert len(result_files) == 2
    assert GLAMBDA_RESULT_FILE in result_files
    assert 'testdir' in result_files

    files_in_testdir = os.listdir(os.path.join(result_directory, 'testdir'))
    assert len(files_in_testdir) == 1
    assert 'testfile' in files_in_testdir

    with open(os.path.join(result_directory, 'testdir', 'testfile'), 'rb') as f:
        assert f.read() == TESTSTRING

async def test_directory_file_output(controller):
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
    # There should be only a single result array for a single task
    assert len(results) == 1

    result_directory = results[0]
    result_files = os.listdir(result_directory)

    assert len(result_files) == 3
    assert GLAMBDA_RESULT_FILE in result_files
    assert 'testdir' in result_files
    assert 'testfile_top' in result_files

    files_in_testdir = os.listdir(os.path.join(result_directory, 'testdir'))
    assert len(files_in_testdir) == 1
    assert 'testfile' in files_in_testdir

    with open(os.path.join(result_directory, 'testdir', 'testfile'), 'rb') as f:
        assert f.read() == TESTSTRING

datadir = '{home}/Projects/golem/node_A/rinkeby'.format(home=Path.home())

controller = RPCController(
    RPCComponent(
        cli_secret='{datadir}/crossbar/secrets/golemcli.tck'.format(datadir=datadir),
        rpc_cert='{datadir}/crossbar/rpc_cert.pem'.format(datadir=datadir)
    )
)
controller.start()

async def test_suite(controller):
    await test_no_output(controller)
    await test_big_file_output(controller)
    await test_task_result_output(controller)
    await test_directory_output(controller)
    await test_directory_file_output(controller)

loop = asyncio.get_event_loop()
loop.run_until_complete(test_suite(controller))

controller.stop()
