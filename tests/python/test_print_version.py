"""--print-version prints the stamp the generators would emit, and writes nothing.

A consumer that only needs the version, such as a CI job comparing it with a deployed peer's,
should not have to generate Markdown and scrape its Version line.
Run with: python3 -m unittest discover -s tests/python
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
from messgen.parser import load_modules
from messgen.version_protocol import VersionProtocol

VENDOR = "test_vendor"
FIRST = VENDOR + "/first"
SECOND = VENDOR + "/second"
UNSTAMPED = VENDOR + "/unstamped"


class PrintVersionTest(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.basedir)
        self.write_module(FIRST, "proto_id: 1\n", "uint32")
        self.write_module(SECOND, "proto_id: 2\n", "uint64")
        self.write_module(UNSTAMPED, "proto_id: 3\ngenerate_protocol_version: false\n", "uint8")

    def write_module(self, module, protocol_yaml, field_type):
        module_dir = os.path.join(self.basedir, module)
        os.makedirs(module_dir)
        with open(os.path.join(module_dir, "_protocol.yaml"), "w") as f:
            f.write(protocol_yaml)
        with open(os.path.join(module_dir, "msg.yaml"), "w") as f:
            f.write("id: 0\nfields:\n  - name: value\n    type: %s\n" % field_type)

    def expected(self, module):
        modules_map = load_modules([self.basedir], [module])
        DataTypesPreprocessor(generate.PLAIN_TYPES, generate.SPECIAL_TYPES).create_types_map(modules_map)
        return VersionProtocol(modules_map[module]).generate()

    def run_generate(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "generate.py"), "-b", self.basedir, *args],
            cwd=self.basedir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def test_prints_only_the_version(self):
        result = self.run_generate("-m", FIRST, "--print-version")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(self.expected(FIRST) + "\n", result.stdout)

    def test_matches_the_markdown_version_line(self):
        outdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outdir)
        # MdGenerator writes vendor/module.md without creating vendor/ first.
        os.makedirs(os.path.join(outdir, VENDOR))
        self.run_generate("-m", FIRST, "-l", "md", "-o", outdir)
        with open(os.path.join(outdir, FIRST + ".md")) as f:
            doc = f.read()
        printed = self.run_generate("-m", FIRST, "--print-version").stdout.strip()
        self.assertIn("\nVersion %s\n" % printed, doc)

    def test_one_line_per_module_in_the_order_given(self):
        result = self.run_generate("-m", SECOND, FIRST, "--print-version")
        self.assertEqual([self.expected(SECOND), self.expected(FIRST)], result.stdout.split())
        self.assertNotEqual(self.expected(FIRST), self.expected(SECOND))

    def test_writes_no_files(self):
        before = sorted(os.walk(self.basedir))
        self.run_generate("-m", FIRST, "--print-version")
        self.assertEqual(before, sorted(os.walk(self.basedir)))

    def test_unstamped_module_fails_before_printing_anything(self):
        result = self.run_generate("-m", FIRST, UNSTAMPED, "--print-version")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn(self.expected(FIRST), result.stdout)
        self.assertIn("generate_protocol_version", result.stdout)

    def test_cannot_be_combined_with_a_language(self):
        result = self.run_generate("-m", FIRST, "-l", "md", "--print-version")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("not allowed", result.stderr)


if __name__ == "__main__":
    unittest.main()
