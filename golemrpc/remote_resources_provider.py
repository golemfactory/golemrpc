import asyncio
import os
from pathlib import PurePath


class RemoteResourcesProvider:
    def __init__(self, root, rpc, meta, transport):
        self.root = root
        self.rpc = rpc
        self.meta = meta
        self.transport = transport

    async def create(self, task):
        resources = []
        if 'resources' in task or 'resources_mapped' in task:
            await self.rpc.call('fs.mkdir', self.root.as_posix())

        if 'resources' in task:
            resources += await self.upload(task['resources'], self.root)

        if 'resources_mapped' in task:
            resources += await self.upload(task['resources_mapped'], self.root)

        return resources

    async def clear(self):
        try:
            await self.rpc.call('fs.removetree', self.root.as_posix())
        except:
            pass

    async def upload(self, resources, dest_root):
        _syspath = self.meta['syspath']
        _resources = []

        if isinstance(resources, dict):
            for src, dest in resources.items():
                src = PurePath(src)
                if dest:
                    dest = PurePath(dest)

                    # Support only relative paths. Relation root on provider
                    # side is '/golem/resources'. Absolute paths are not
                    # supported because it's not clear how paths like
                    # 'C:/file.txt' or '/home/user/file.txt' should be handled.
                    assert not dest.is_absolute(), (
                        'only relative paths are allowed '
                        'as mapping values {}'.format(dest.as_posix()))

                    parents = list(dest.parents)

                    # Removing last element because it's a root (current
                    # directory, for posix it's '.')
                    parents = [
                        p for p in parents[:-1]
                    ]
                    # Now parents should contain a growing directory sequence
                    # for path 'a/b/c' that will be ['a', 'a/b']

                    if parents:
                        # Recreate directory structure stored in `parents` on remote side
                        for anchor in reversed(parents):
                            await self.rpc.call('fs.mkdir',
                                                (dest_root / anchor).as_posix())
                    remote_path = dest_root / dest
                    await self.transport.upload(src.as_posix(),
                                                remote_path.as_posix())

                    if parents:
                        # If there is a directory structure defined in mapping
                        # then a resource path should point to it's last anchor e.g.
                        # 'dir1/dir2/foo` should yield `dir1`.
                        resources_dir_path = _syspath / dest_root / parents[-1]
                    else:
                        resources_dir_path = _syspath / dest_root / dest

                    _resources.append(resources_dir_path.as_posix())

                else:
                    remote_path = dest_root / src.name
                    await self.transport.upload(src.as_posix(),
                                                remote_path.as_posix())
                    _resources.append((_syspath / remote_path).as_posix())

            return _resources

        elif isinstance(resources, list):
            for r in resources:
                r = PurePath(r)
                # Place resources on remote filesystem root directory
                # e.g. 'foo/bar/file.txt' -> '$dest_root/file.txt'
                remote_path = dest_root / r.name
                await self.transport.upload(r.as_posix(),
                                            remote_path.as_posix())
                # For remote side to pick up resources during task requesting an
                # absolute path to resources has to be put in _resources, e.g.
                # $_syspath = /tmp
                # $dest_root = tempfs1234
                # local resource = foo/bar/file.txt
                # _resource = /tmp/tempfs1234/file.txt
                _resources.append((_syspath / remote_path).as_posix())

            return _resources
        else:
            raise NotImplementedError()

    async def download(self, resources, root):
        os.mkdir(root)

        outs = []
        download_futures = []
        for result in resources:
            dest = os.path.join(root,
                                os.path.basename(result))
            download_futures.append(self.transport.download(result, dest))
            outs.append(dest)

        await asyncio.gather(*download_futures)

        return outs
