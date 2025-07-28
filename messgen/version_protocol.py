import hashlib
import json


def _sanitize(obj):
    """Recursively remove description fields and sort keys for deterministic hashing."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in sorted(obj.items()) if k != "descr"}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


class VersionProtocol:
    def __init__(self, module):
        self._module = module


    def generate(self):
        sanitized = _sanitize(self._module)
        serialized = json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
        result = hashlib.md5(serialized.encode())
        return result.hexdigest()[0:6]
