"""Protocol version must depend on its own module only.

Historically every module generated in one invocation shared an accumulated
"max_datatype_size", so editing one protocol's yaml moved the version stamp of every
protocol listed after it. Run with: python3 -m unittest discover -s tests/python
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import generate
from messgen.data_types_preprocessor import DataTypesPreprocessor
from messgen.parser import load_modules
from messgen.version_protocol import VersionProtocol

VENDOR = "test_vendor"
SMALL = VENDOR + "/small"
BIG = VENDOR + "/big"


def versions(basedir, modules):
    modules_map = load_modules([basedir], modules)
    DataTypesPreprocessor(generate.PLAIN_TYPES, generate.SPECIAL_TYPES).create_types_map(modules_map)
    return {name: VersionProtocol(module).generate() for name, module in modules_map.items()}


class ProtocolVersionTest(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.basedir)

        self.write_module(SMALL, proto_id=1, message="""
id: 0
fields:
  - name: value
    type: uint32
""")
        self.write_module(BIG, proto_id=2, message="""
id: 0
fields:
  - name: payload
    type: uint8[64]
""")

    def write_module(self, module_name, proto_id, message):
        module_dir = os.path.join(self.basedir, module_name)
        if not os.path.exists(module_dir):
            os.makedirs(module_dir)
        with open(os.path.join(module_dir, "_protocol.yaml"), "w") as f:
            f.write("proto_id: %d\n" % proto_id)
        with open(os.path.join(module_dir, "msg.yaml"), "w") as f:
            f.write(message)

    def test_version_does_not_depend_on_sibling_modules(self):
        alone = versions(self.basedir, [SMALL])[SMALL]
        self.assertEqual(alone, versions(self.basedir, [SMALL, BIG])[SMALL])
        self.assertEqual(alone, versions(self.basedir, [BIG, SMALL])[SMALL])

    def test_version_does_not_depend_on_sibling_module_content(self):
        before = versions(self.basedir, [BIG, SMALL])[SMALL]

        self.write_module(BIG, proto_id=2, message="""
id: 0
fields:
  - name: payload
    type: uint8[128]
  - name: extra
    type: uint64
""")

        self.assertEqual(before, versions(self.basedir, [BIG, SMALL])[SMALL])

    def test_version_depends_on_own_content(self):
        before = versions(self.basedir, [SMALL, BIG])[SMALL]

        self.write_module(SMALL, proto_id=1, message="""
id: 0
fields:
  - name: value
    type: uint64
""")

        self.assertNotEqual(before, versions(self.basedir, [SMALL, BIG])[SMALL])

    def test_version_ignores_descriptions(self):
        before = versions(self.basedir, [SMALL])[SMALL]

        self.write_module(SMALL, proto_id=1, message="""
id: 0
descr: some message
fields:
  - name: value
    type: uint32
    descr: some field
""")

        self.assertEqual(before, versions(self.basedir, [SMALL])[SMALL])

    def test_max_datatype_size_is_per_module(self):
        modules_map = load_modules([self.basedir], [BIG, SMALL])
        DataTypesPreprocessor(generate.PLAIN_TYPES, generate.SPECIAL_TYPES).create_types_map(modules_map)

        self.assertEqual(64, modules_map[BIG]["max_datatype_size"])
        self.assertEqual(4, modules_map[SMALL]["max_datatype_size"])


if __name__ == "__main__":
    unittest.main()
