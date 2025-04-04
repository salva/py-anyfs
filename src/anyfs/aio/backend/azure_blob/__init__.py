import anyio
import httpx

from anyfs.aio.base import _ANode, _AFS

from azure.identity.aio import DefaultAzureCredential

class _AAzureBlobNode(_ANode):
    async def is_root(self):
        return self._fs._is_root_node(self)

    async def is_dir(self):
        return False

    async def is_file(self):
        return False

    async def list(self):
        raise_enotsup(self._path, "list")

    async def stat(self):
        raise_enotsup(self._path, "stat")

    async def slurp(self):
        raise_enotsup(self._path, "slurp")

class AAzureBlobFS(_AFS):

    def __init__(self,
                 identity=None,
                 account=None,
                 container=None,
                 host=None,
                 url=None,
                 cache_size=1000, cache_ttl=120):
        super().__init__(root=None, cache_size=cache_size, cache_ttl=cache_ttl)
        if identity is None:
            identity = DefaultAzureCredential()

        if url is None:
            if host is None:
                if account is None:
                    raise ValueError("url, host or account is required")
                host = f"{account}.blob.core.windows.net"
            if container is None:
                raise ValueError("container is required")
            url = f"https://{host}/{container}/"
        else:
            if not url.endswith("/"):
                url += "/"
            if container is not None:
                url += container + "/"
        self._url = url
        self._container = container
        self._identity = identity
        self._client = httpx.AsyncClient()

    async def _before_make_node(self, path):
        self._http_client.send('get', path)
        return None

    async def _before_make_node(self, path):
        pass
