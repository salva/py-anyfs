from anyfs.aio.base import _AFS, _ANode

import os
import stat
import pathlib
from anyfs.errors import *

class _ALocalNode(_ANode):
    def __init__(self, fs, path, stats):
        super().__init__(fs, path)
        self._stats = stats
        print(f"stats: {stats}")

    async def is_dir(self):
        return stat.S_ISDIR(self._stats.st_mode)

    async def is_file(self):
        return stat.S_ISREG(self._stats.st_mode)

    async def list(self):
        await self.require_dir()
        return os.listdir(self._path)

    async def stat(self):
        return os.stat_object(self._stats)

    async def slurp(self, encoding="utf-8"):
        await self.require_file()
        if encoding is not None:
            mode = "r"
        else:
            mode = "rb"
        with open(self._path, mode, encoding=encoding) as f:
            return f.read()

class ALocalFS(_AFS):
    _node_class = _ALocalNode
    _path_class = pathlib.PurePath

    def __init__(self, root=None):
        if root is None:
            root = "C:\\" if os.name == "nt" else "/"
        super().__init__(root=root, cache_size=0)

    async def root(self):
        return await self._node(self._root_path)

    async def _before_make_node(self, path):
        return os.stat(path)


