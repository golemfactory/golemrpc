import os

from utils import create_rpc_component


class TransferManager(object):
    def __init__(self, rpc_component):
        self.rpc_component = rpc_component
        self.chunk_size = rpc_component.post_wait({
            'type': 'RPCCall',
            'method_name': 'fs.meta',
            'args': []
        })['chunk_size']

    def upload(self, src, dest):
        upload_id = self.rpc_component.post_wait({
            'type': 'RPCCall',
            'method_name': 'fs.upload_id',
            'args': [
                os.path.basename(dest)
            ]
        })
        with open(src, 'rb') as f:
            while True:
                data = f.read(self.chunk_size)

                if not data:
                    break

                count = self.rpc_component.post_wait({
                    'type': 'RPCCall',
                    'method_name': 'fs.upload',
                    'args': [
                        upload_id,
                        data
                    ]
                })
                if count != len(data):
                    raise RuntimeError(
                        'Error uploading data, lenghts do not match')

                if len(data) < self.chunk_size:
                    break

    def download(self, src, dest):
        download_id = self.rpc_component.post_wait({
            'type': 'RPCCall',
            'method_name': 'fs.download_id',
            'args': {
                os.path.basename(src)
            }
        })
        with open(dest, 'wb') as f:
            while True:
                data = self.rpc_component.post_wait({
                    'type': 'RPCCall',
                    'method_name': 'fs.download',
                    'args': [
                        download_id
                    ]
                })

                f.write(data)

                if len(data) != self.chunk_size:
                    break


def test_transfer_manager():
    src = '/usr/bin/snap'
    result = 'tmp2'
    rpc_component = create_rpc_component()
    rpc_component.start()
    transfer_mgr = TransferManager(rpc_component)
    transfer_mgr.upload(src, 'tmp')
    transfer_mgr.download('tmp', result)

    src_size = os.stat(src).st_size
    result_size = os.stat(result).st_size

    os.remove(result)

    assert src_size == result_size


def test_big_file_upload():
    src = 'test_big'
    result = 'result_big'
    with open(src, 'wb') as f:
        # 4 GB
        f.seek(4 * 1024 * 1024 * 1024 - 1)
        f.write(b"\0")

    rpc_component = create_rpc_component()
    rpc_component.start()

    transfer_mgr = TransferManager(rpc_component)
    transfer_mgr.upload(src, 'tmp_big_file')
    transfer_mgr.download('tmp_big_file', result)

    src_size = os.stat(src).st_size
    result_size = os.stat(result).st_size

    os.remove(src)
    os.remove(result)

    assert src_size == result_size
