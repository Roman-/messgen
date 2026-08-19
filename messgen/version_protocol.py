import hashlib
import json

# Keys that must never influence the protocol version.
#   "descr"             - documentation, rewording it is not a protocol change.
#   "max_datatype_size" - derived by DataTypesPreprocessor from the module's own
#                         messages, so it carries no information the hash does not
#                         already cover. It is excluded explicitly because it used
#                         to accumulate across every module of a single generator
#                         invocation, which made each protocol version depend on the
#                         yaml of the unrelated protocols listed before it.
IGNORED_KEYS = frozenset(("descr", "max_datatype_size"))


def _sanitize(obj):
    """Recursively remove ignored fields and sort keys for deterministic hashing."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in sorted(obj.items()) if k not in IGNORED_KEYS}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


class VersionProtocol:
    """Hashes a single module's definition.

    The result depends only on that module, so generating several protocols in one
    invocation must not move any of their versions.
    """

    def __init__(self, module):
        self._module = module


    def generate(self):
        sanitized = _sanitize(self._module)
        serialized = json.dumps(sanitized, sort_keys=True, separators=(",", ":"))
        result = hashlib.md5(serialized.encode())
        return result.hexdigest()[0:6]
