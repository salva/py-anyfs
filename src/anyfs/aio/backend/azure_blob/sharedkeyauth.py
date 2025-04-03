import base64
import hashlib
import hmac
from datetime import datetime
from httpx import Auth, Request
from urllib.parse import urlparse, parse_qs


class AzureSharedKeyAuth(Auth):
    def __init__(self, account_name: str, account_key: str):
        self.account_name = account_name
        self.account_key = base64.b64decode(account_key)

    def auth_flow(self, request: Request):
        # Add x-ms-date and x-ms-version headers
        x_ms_date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        request.headers['x-ms-date'] = x_ms_date
        request.headers.setdefault('x-ms-version', '2019-07-07')

        # Extract components needed for signing
        url = urlparse(str(request.url))
        account_name = self.account_name
        path = url.path or '/'
        canonicalized_resource = f"/{account_name}{path}"

        # Canonicalize query string parameters
        query_params = parse_qs(url.query)
        if query_params:
            for key in sorted(query_params):
                values = query_params[key]
                canonicalized_resource += f"\n{key.lower()}:{','.join(sorted(values))}"

        # Canonicalized headers (only those starting with x-ms-)
        x_ms_headers = {
            k.lower(): v.strip()
            for k, v in request.headers.items()
            if k.lower().startswith('x-ms-')
        }
        canonicalized_headers = ''.join(
            f"{k}:{x_ms_headers[k]}\n" for k in sorted(x_ms_headers)
        )

        # Content-Length must be empty string if 0
        content_length = request.headers.get("Content-Length", "")
        if content_length == "0":
            content_length = ""

        # Build the StringToSign
        string_to_sign = (
            f"{request.method}\n"
            f"{request.headers.get('Content-Encoding', '')}\n"
            f"{request.headers.get('Content-Language', '')}\n"
            f"{content_length}\n"
            f"{request.headers.get('Content-MD5', '')}\n"
            f"{request.headers.get('Content-Type', '')}\n"
            f"\n"  # Date is empty because x-ms-date is used
            f"{request.headers.get('If-Modified-Since', '')}\n"
            f"{request.headers.get('If-Match', '')}\n"
            f"{request.headers.get('If-None-Match', '')}\n"
            f"{request.headers.get('If-Unmodified-Since', '')}\n"
            f"{request.headers.get('Range', '')}\n"
            f"{canonicalized_headers}"
            f"{canonicalized_resource}"
        )

        # Compute the signature
        signed_hmac_sha256 = hmac.new(
            self.account_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).digest()
        signature = base64.b64encode(signed_hmac_sha256).decode()

        # Build Authorization header
        auth_string = f"SharedKey {account_name}:{signature}"
        request.headers['Authorization'] = auth_string

        yield request
