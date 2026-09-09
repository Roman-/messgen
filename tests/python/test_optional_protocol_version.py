"""generate_protocol_version: false drops the version stamp from every generator.

A protocol whose peers agree on their wire format by other means gets no use out of the
generated stamp, and a field rename would otherwise read as a protocol event to anyone
grepping for it. Run with: python3 -m unittest discover -s tests/python
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

import generate
from messgen.data_types_preprocessor import DataTypesPreprocessor
from messgen.messgen_ex import MessgenException
from messgen.parser import load_modules
from messgen.version_protocol import VersionProtocol

VENDOR = "test_vendor"
MODULE = VENDOR + "/stamped"

MESSAGE = """
id: 0
fields:
  - name: value
    type: uint32
"""


class OptionalProtocolVersionTest(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.basedir)

    def write_module(self, protocol_yaml):
        module_dir = os.path.join(self.basedir, MODULE)
        if not os.path.exists(module_dir):
            os.makedirs(module_dir)
        with open(os.path.join(module_dir, "_protocol.yaml"), "w") as f:
            f.write(protocol_yaml)
        with open(os.path.join(module_dir, "msg.yaml"), "w") as f:
            f.write(MESSAGE)

    def load(self):
        modules_map = load_modules([self.basedir], [MODULE])
        DataTypesPreprocessor(generate.PLAIN_TYPES, generate.SPECIAL_TYPES).create_types_map(modules_map)
        return modules_map[MODULE]

    def generate_lang(self, lang):
        outdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outdir)
        # MdGenerator writes vendor/module.md without creating vendor/ first.
        os.makedirs(os.path.join(outdir, VENDOR))
        subprocess.check_output(
            [sys.executable, os.path.join(REPO_ROOT, "generate.py"),
             "-b", self.basedir, "-m", MODULE, "-l", lang, "-o", outdir],
            stderr=subprocess.STDOUT)
        return outdir

    def test_absent_key_defaults_to_generating(self):
        self.write_module("proto_id: 1\n")
        self.assertTrue(self.load()["generate_protocol_version"])

    def test_explicit_true_leaves_the_version_where_it_was(self):
        self.write_module("proto_id: 1\n")
        implied = VersionProtocol(self.load()).generate()

        self.write_module("proto_id: 1\ngenerate_protocol_version: true\n")
        self.assertEqual(implied, VersionProtocol(self.load()).generate())

    def test_non_boolean_value_is_rejected(self):
        self.write_module("proto_id: 1\ngenerate_protocol_version: no_thanks\n")
        with self.assertRaises(MessgenException) as ctx:
            self.load()
        self.assertIn("generate_protocol_version", str(ctx.exception))

    def test_cpp_omits_the_stamp(self):
        self.write_module("proto_id: 1\ngenerate_protocol_version: false\n")
        proto_h = os.path.join(self.generate_lang("cpp"), VENDOR, "msgs", "stamped", "proto.h")
        with open(proto_h) as f:
            code = f.read()
        self.assertNotIn("VERSION", code)
        self.assertIn("PROTO_ID = 1;", code)

    def test_cpp_emits_the_stamp_by_default(self):
        self.write_module("proto_id: 1\n")
        proto_h = os.path.join(self.generate_lang("cpp"), VENDOR, "msgs", "stamped", "proto.h")
        with open(proto_h) as f:
            code = f.read()
        version = VersionProtocol(self.load()).generate()
        self.assertIn("static constexpr const char* VERSION = \"%s\";" % version, code)
        self.assertIn("static constexpr const char* PROTO_VERSION = \"%s\";" % version, code)

    def test_md_omits_the_version_line(self):
        self.write_module("proto_id: 1\ngenerate_protocol_version: false\n")
        with open(os.path.join(self.generate_lang("md"), MODULE + ".md")) as f:
            doc = f.read()
        self.assertNotIn("Version", doc)
        self.assertIn("# %s\n\n|" % MODULE, doc)

    def test_md_emits_the_version_line_by_default(self):
        self.write_module("proto_id: 1\n")
        with open(os.path.join(self.generate_lang("md"), MODULE + ".md")) as f:
            doc = f.read()
        self.assertIn("Version %s" % VersionProtocol(self.load()).generate(), doc)

    def test_json_writes_no_version_file(self):
        self.write_module("proto_id: 1\ngenerate_protocol_version: false\n")
        module_dir = os.path.join(self.generate_lang("json"), VENDOR, "stamped")
        self.assertTrue(os.path.exists(os.path.join(module_dir, "messages.json")))
        self.assertFalse(os.path.exists(os.path.join(module_dir, "version.json")))

    def test_json_writes_the_version_file_by_default(self):
        self.write_module("proto_id: 1\n")
        module_dir = os.path.join(self.generate_lang("json"), VENDOR, "stamped")
        with open(os.path.join(module_dir, "version.json")) as f:
            self.assertEqual(VersionProtocol(self.load()).generate(), json.load(f)["version"])


if __name__ == "__main__":
    unittest.main()
