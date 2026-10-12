import gzip
import urllib.error
import urllib.request


def fetch(url, timeout=25, headers=None, data=None):
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "DGED-Atlas/0.1 (inteligencia operativa; contacto local)",
            "Accept": "*/*",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            if body[:2] == b"\x1f\x8b":
                body = gzip.decompress(body)
            return {
                "ok": True,
                "status": response.status,
                "url": response.geturl(),
                "content_type": response.headers.get("Content-Type", ""),
                "body": body,
            }
    except urllib.error.HTTPError as error:
        return {
            "ok": False,
            "status": error.code,
            "url": url,
            "content_type": error.headers.get("Content-Type", "") if error.headers else "",
            "body": error.read() if error.fp else b"",
            "error": str(error),
        }
    except Exception as error:
        return {
            "ok": False,
            "status": 0,
            "url": url,
            "content_type": "",
            "body": b"",
            "error": str(error),
        }
