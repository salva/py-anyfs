import anyio
from abc import abstractmethod

import httpx
from urllib.parse import urljoin
import logging
import pathlib
import cachetools
from anyfs.errors import *

class _ANode:
    def __init__(self, fs, path):
        self._fs = fs
        self._path = path

    async def is_root(self):
        return self._fs._is_root_node(self)

    async def is_dir(self):
        return False

    async def is_file(self):
        return False

    async def require_dir(self):
        if not await self.is_dir():
            raise_enotdir(self._path)

    async def require_file(self):
        if not await self.is_file():
            raise_enotfile(self._path)

    def parent(self): #async tail call
        return self._fs._parent_node(self)

    async def go(self, path):
        await self.require_dir()
        return await self._fs._go(self, path)

    async def _child(self, name):
        await self.require_dir()
        return await self._fs._child_node(self, name)

    async def slurp(self):
        raise_enotsup(self._path, "slurp")

    async def list(self):
        raise_enotsup(self._path, "list")

    async def mkdir(self, path, exist_ok=False):
        raise_enotsup(self._path, "mkdir")

    async def reload(self):
        pass

class _AFS:

    _path_class = pathlib.PurePosixPath
    _node_class = _ANode

    def __init__(self, root=None, cache_size=1000, cache_ttl=120):
        if root is None:
            root = "/"
        self._root_path = self._path_class(root)
        self._node_cache = ( cachetools.LRUCache(maxsize=cache_size, ttl=cache_ttl)
                             if cache_size > 0 and cache_ttl > 0
                             else None )

    def root(self):
        return self._node(self._root_path)

    def _is_root_node(self, node):
        return node._path == self._root_path

    def _child_path(self, parent, name):
        return parent._path / name

    def _child_node(self, parent, name): # async tail call
        path = self._child_path(parent, name)
        return self._node(path)

    async def _parent_node(self, node):
        if self._is_root_node(node):
            return node
        return await self._node(node._path.parent)

    async def _node(self, path, cached=True, **kwargs):
        if cached:
            if (node_cache := self._node_cache) is not None:
                if (node := node_cache.get(path)) is not None:
                    return node

        node = await self._make_node(path, **kwargs)
        if node is None:
            raise FileNotFoundError(path)
        if node_cache is not None:
            node_cache[path] = node
        return node

    async def _make_node(self, path):
        inner_data = await self._before_make_node(path)
        return self._node_class(self, path, inner_data)

    async def _before_make_node(self, path):
        return None

    async def _go(self, node, path):
        path = self._path_class(path)
        # TODO: Windows compatibility
        if path.is_absolute():
            node = await self.root()
            path = path.relative_to(node._path)
        for part in path.parts:
            if part == "..":
                node = await node.parent()
            elif part == ".":
                continue
            else:
                node = await node._child(part)

        return node

default_http_timeout = 10
default_http_retry_max_attempts = 4
default_http_retry_delay = 2
default_http_retry_delay_factor = 1.5
default_http_transitory_codes = {
    httpx.codes.REQUEST_TIMEOUT,
    httpx.codes.TOO_MANY_REQUESTS,
    httpx.codes.INTERNAL_SERVER_ERROR,
    httpx.codes.BAD_GATEWAY,
    httpx.codes.SERVICE_UNAVAILABLE,
    httpx.codes.GATEWAY_TIMEOUT
}

class AFSWithHTTPClient(_AFS):
    def __init__(self, *args,
                 base_url=None,
                 http_timeout=default_http_timeout,
                 http_retry_max_attempts=default_http_retry_max_attempts,
                 http_retry_delay=default_http_retry_delay,
                 http_retry_delay_factor=default_http_retry_delay_factor,
                 _http_transitory_codes=default_http_transitory_codes,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._http_client = httpx.AsyncClient(base_url=base_url,
                                              timeout=http_timeout)
        self._http_retry_max_attempts = http_retry_max_attempts
        self._http_retry_delay = http_retry_delay
        self._http_retry_delay_factor = http_retry_delay_factor
        self._http_transitory_codes = _http_transitory_codes


    async def _auth_headers(self):
        raise NotImplementedError("auth_headers")

    async def _send(self, method, url, fspath=None, accepted_code=None, json=None, headers={}, authorize=True, **kwargs):
        client = self._http_client

        if authorize:
            auth_headers = await self->_auth_headers()
            headers = {**headers, **auth_headers}

        if "content" in kwargs:
            headers.setdefault("Content-Type", "application/octet-stream")

        if fspath is None:
            fspath = url

        http_retry_delay = self._http_retry_delay
        http_retry_max_attempts = self._http_retry_max_attempts
        http_retry_delay_factor = self._http_retry_delay_factor
        http_transitory_http_codes = self._http_transitory_http_codes

        call = getattr(client, method)
        attempt = 1
        while True:
            try:
                res = await call(url, headers, **kwargs)
            except: httpx.RequestError as ex:
                logging.error(f"HTTP request {method} {url} failed, attempt: {attempt}", exc_info=ex)
                if attempt >= http_retry_max_attempts:
                    raise_eio(fspath)
            else:
                status_code = res.status_code
                if accepted_codes is None:
                    if status_code < 300:
                        return res
                else:
                    if status_code in accepted_codes:
                        return res

                logging.error(f"HTTP request {method} {url} failed, code: {status_code}, attempt {attempt}")
                if ((attempt >= http_retry_max_attempts) or
                    (status_code not in http_transitory_http_codes)):
                    if status_code == httpx.codes.FORBIDDEN:
                        raise_eacces(fspath)
                    raise_eio(fspath)

            await anyio.sleep(self.http_retry_delay)
            http_retry_delay = int(http_retry_delay * http_retry_delay_factor + 1)
            attempt += 1
