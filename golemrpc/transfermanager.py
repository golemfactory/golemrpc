import os
from pathlib import PurePath


class TransferManager(object):
    def __init__(self, rpc, meta):
        self.rpc = rpc
        self.chunk_size = meta['chunk_size']
        self.path_ser = lambda path: PurePath(path).as_posix()

    async def upload(self, src, dest):
        if os.path.isdir(src):
            await self.rpc.call('fs.mkdir', self.path_ser(dest))
            file_list = [
                os.path.normpath(f) for f in
                os.listdir(src)
            ]
            for f in file_list:
                await self.upload(
                    os.path.join(src, f),
                    os.path.join(dest, f)
                )
        else:
            await self.upload_file(src, dest)

    async def upload_file(self, src, dest):
        upload_id = await self.rpc.call('fs.upload_id', self.path_ser(dest))
        with open(src, 'rb') as f:
            while True:
                data = f.read(self.chunk_size)

                if not data:
                    break
                count = await self.rpc.call('fs.upload', upload_id, data)
                if count != len(data):
                    raise RuntimeError(
                        'Error uploading data, lenghts do not match')

                if len(data) < self.chunk_size:
                    break

    async def download(self, src, dest):
        if await self.rpc.call('fs.isdir', self.path_ser(src)):
            os.mkdir(dest)
            file_list = await self.rpc.call('fs.listdir', self.path_ser(src))
            file_list[:] = [PurePath(f) for f in file_list]
            for f in file_list:
                await self.download(
                    os.path.join(src, f),
                    os.path.join(dest, f)
                )
        else:
            await self.download_file(src, dest)

    async def download_file(self, src, dest):
        download_id = await self.rpc.call('fs.download_id',
                                          self.path_ser(src))
        with open(dest, 'wb') as f:
            while True:
                data = await self.rpc.call('fs.download', download_id)
                f.write(data)

                if len(data) != self.chunk_size:
                    break
