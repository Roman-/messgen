"""check_field_order: true fails generation when a message's yaml field order is not the generated one.

The generated order is the wire order, and a peer that reads the yaml in declaration order (messgen
v1 does) sees a different layout wherever the two differ. Run with:
python3 -m unittest discover -s tests/python
"""

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

CHECKED = "test_vendor/checked"
UNCHECKED = "test_vendor/unchecked"

# Generated order: scalars by alignment descending, then nested messages, then dynamic fields.
IN_ORDER = """
id: 0
fields:
  - name: wide
    type: uint32
  - name: narrow
    type: uint8
  - name: text
    type: string
"""

OUT_OF_ORDER = """
id: 1
fields:
  - name: text
    type: string
  - name: narrow
    type: uint8
  - name: wide
    type: uint32
"""


class FieldOrderCheckTest(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.basedir)

    def write_module(self, module, protocol_yaml, messages):
        module_dir = os.path.join(self.basedir, module)
        os.makedirs(module_dir)
        with open(os.path.join(module_dir, "_protocol.yaml"), "w") as f:
            f.write(protocol_yaml)
        for name, yaml in messages.items():
            with open(os.path.join(module_dir, name + ".yaml"), "w") as f:
                f.write(yaml)

    def load(self, modules):
        modules_map = load_modules([self.basedir], modules)
        DataTypesPreprocessor(generate.PLAIN_TYPES, generate.SPECIAL_TYPES).create_types_map(modules_map)
        return modules_map

    def test_absent_key_allows_any_order(self):
        self.write_module(CHECKED, "proto_id: 1\n", {"in_order": IN_ORDER, "out_of_order": OUT_OF_ORDER})
        self.assertFalse(self.load([CHECKED])[CHECKED]["check_field_order"])

    def test_non_boolean_value_is_rejected(self):
        self.write_module(CHECKED, "proto_id: 1\ncheck_field_order: yes_please\n", {"in_order": IN_ORDER})
        with self.assertRaises(MessgenException) as ctx:
            self.load([CHECKED])
        self.assertIn("check_field_order", str(ctx.exception))

    def test_generated_order_passes(self):
        self.write_module(CHECKED, "proto_id: 1\ncheck_field_order: true\n", {"in_order": IN_ORDER})
        self.load([CHECKED])

    def test_other_order_fails_and_names_the_generated_order(self):
        self.write_module(CHECKED, "proto_id: 1\ncheck_field_order: true\n",
                          {"in_order": IN_ORDER, "out_of_order": OUT_OF_ORDER})
        with self.assertRaises(MessgenException) as ctx:
            self.load([CHECKED])
        self.assertIn("test_vendor/checked/out_of_order: wide, narrow, text", str(ctx.exception))
        self.assertNotIn("in_order:", str(ctx.exception))

    def test_nested_message_goes_after_every_scalar(self):
        self.write_module(CHECKED, "proto_id: 1\ncheck_field_order: true\n", {
            "inner": IN_ORDER,
            "outer": "id: 1\nfields:\n  - name: inner\n    type: inner\n  - name: flag\n    type: uint8\n",
        })
        with self.assertRaises(MessgenException) as ctx:
            self.load([CHECKED])
        self.assertIn("test_vendor/checked/outer: flag, inner", str(ctx.exception))

    def test_message_loaded_first_by_another_module_is_still_checked(self):
        # unchecked is processed first and loads checked/out_of_order as its field type, which sorts
        # that message's fields before the loop over checked's messages reaches it.
        self.write_module(CHECKED, "proto_id: 1\ncheck_field_order: true\n", {"out_of_order": OUT_OF_ORDER})
        self.write_module(UNCHECKED, "proto_id: 2\n", {
            "holder": "id: 0\nfields:\n  - name: held\n    type: test_vendor/checked/out_of_order\n",
        })
        with self.assertRaises(MessgenException) as ctx:
            self.load([UNCHECKED, CHECKED])
        self.assertIn("test_vendor/checked/out_of_order", str(ctx.exception))

    def test_unchecked_module_is_not_checked_through_a_checked_one(self):
        self.write_module(UNCHECKED, "proto_id: 2\n", {"out_of_order": OUT_OF_ORDER})
        self.write_module(CHECKED, "proto_id: 1\ncheck_field_order: true\n", {
            "holder": "id: 0\nfields:\n  - name: held\n    type: test_vendor/unchecked/out_of_order\n",
        })
        self.load([CHECKED, UNCHECKED])

    def test_key_leaves_the_version_where_it_was(self):
        self.write_module(CHECKED, "proto_id: 1\n", {"in_order": IN_ORDER})
        unchecked = VersionProtocol(self.load([CHECKED])[CHECKED]).generate()

        with open(os.path.join(self.basedir, CHECKED, "_protocol.yaml"), "w") as f:
            f.write("proto_id: 1\ncheck_field_order: true\n")
        self.assertEqual(unchecked, VersionProtocol(self.load([CHECKED])[CHECKED]).generate())

    def test_generate_fails(self):
        self.write_module(CHECKED, "proto_id: 1\ncheck_field_order: true\n", {"out_of_order": OUT_OF_ORDER})
        outdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outdir)
        result = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "generate.py"),
             "-b", self.basedir, "-m", CHECKED, "-l", "cpp", "-o", outdir],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("out_of_order: wide, narrow, text", result.stdout)
        self.assertEqual([], os.listdir(outdir))


if __name__ == "__main__":
    unittest.main()
