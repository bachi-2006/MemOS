import httpx

# Compatibility patch for Starlette < 0.28 with HTTPX >= 0.28
_orig_init = httpx.Client.__init__

def _patched_client_init(self, *args, **kwargs):
    app = kwargs.pop("app", None)
    if app is not None and "transport" not in kwargs:
        kwargs["transport"] = httpx.ASGITransport(app=app)
    _orig_init(self, *args, **kwargs)

if "app" not in httpx.Client.__init__.__code__.co_varnames:
    httpx.Client.__init__ = _patched_client_init
