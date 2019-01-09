import os
from pathlib import Path

from utils import create_rpc_component

filename = '/usr/bin/snap'

input_chunks = []

class TransferManager(object):
    def __init__(self, rpc_component):
        self.rpc_component = rpc_component
        self.chunk_size = rpc_component.evaluate_sync({
            'type': 'rpc_call',
            'method_name': 'fs.meta',
            'args': []
        })['chunk_size']

    def upload(self, filename, dest):
        upload_id = self.rpc_component.evaluate_sync({
            'type': 'rpc_call',
            'method_name': 'fs.upload_id',
            'args': [
                os.path.basename(dest)
            ]
        })
        with open(filename, 'rb') as f:
            while True:
                data = f.read(self.chunk_size)

                if not data:
                    break

                count = self.rpc_component.evaluate_sync({
                    'type': 'rpc_call',
                    'method_name': 'fs.upload',
                    'args': [
                        upload_id,
                        data
                    ]
                })
                if count != len(data):
                    raise RuntimeError('Error uploading data, lenghts do not match')

                input_chunks.append(data)

                if len(data) < self.chunk_size:
                    break
    def download(self, filename, dest):
        download_id = self.rpc_component.evaluate_sync({
            'type': 'rpc_call',
            'method_name': 'fs.download_id',
            'args': {
                os.path.basename(filename)
            }
        })
        with open(dest, 'wb') as f:
            while True:
                data = self.rpc_component.evaluate_sync({
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
    transfer_mgr = TransferManager(create_rpc_component())
    transfer_mgr.upload('/usr/bin/snap', 'snap')
    transfer_mgr.download('snap', 'snap2')

    assert os.stat('/usr/bin/snap').st_size ==\
            os.stat('snap2').st_size
