import os
from pathlib import Path

from utils import create_rpc_component


class TransferManager(object):
    def __init__(self, rpc_component):
        self.rpc_component = rpc_component
        self.chunk_size = rpc_component.post({
            'type': 'rpc_call',
            'method_name': 'fs.meta',
            'args': []
        })['chunk_size']

    def upload(self, src, dest):
        upload_id = self.rpc_component.post({
            'type': 'rpc_call',
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

                count = self.rpc_component.post({
                    'type': 'rpc_call',
                    'method_name': 'fs.upload',
                    'args': [
                        upload_id,
                        data
                    ]
                })
                if count != len(data):
                    raise RuntimeError('Error uploading data, lenghts do not match')

                if len(data) < self.chunk_size:
                    break

    def download(self, src, dest):
        download_id = self.rpc_component.post({
            'type': 'rpc_call',
            'method_name': 'fs.download_id',
            'args': {
                os.path.basename(src)
            }
        })
        with open(dest, 'wb') as f:
            while True:
                data = self.rpc_component.post({
                    'type': 'rpc_call',
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
    rpc_component = create_rpc_component()
    rpc_component.start()
    transfer_mgr = TransferManager(rpc_component)
    transfer_mgr.upload(src, 'tmp')
    transfer_mgr.download('tmp', 'tmp2')

    assert os.stat(src).st_size ==\
        os.stat('tmp2').st_size
