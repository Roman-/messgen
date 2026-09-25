#!/usr/bin/env python3

import argparse

from messgen.go_generator import GoGenerator
from messgen.json_generator import JsonGenerator
from messgen.ts_generator import TsGenerator
from messgen.md_generator import MdGenerator
from messgen.parser import load_modules, GENERATE_PROTOCOL_VERSION
from messgen.version_protocol import VersionProtocol
from messgen.cpp_generator import CppGenerator
from messgen.data_types_preprocessor import DataTypesPreprocessor
from messgen import MessgenException

MODULE_SEP = "/"

generators = {
    "cpp": CppGenerator,
    "go": GoGenerator,
    "json": JsonGenerator,
    "ts": TsGenerator,
    "md": MdGenerator
}

PLAIN_TYPES = {
    "char": {"size": 1, "align": 1},
    "int8": {"size": 1, "align": 1},
    "uint8": {"size": 1, "align": 1},
    "int16": {"size": 2, "align": 2},
    "uint16": {"size": 2, "align": 2},
    "int32": {"size": 4, "align": 4},
    "uint32": {"size": 4, "align": 4},
    "int64": {"size": 8, "align": 8},
    "uint64": {"size": 8, "align": 8},
    "float32": {"size": 4, "align": 4},
    "float64": {"size": 8, "align": 8},
}

SPECIAL_TYPES = {
    "string": {"size": 1, "align": 1}
}
def main():
    parser = argparse.ArgumentParser(description='Message generator.')
    parser.add_argument("-b", "--basedirs", required=True, type=str, nargs="+",
                        help='Message definition base directories')
    parser.add_argument("-m", "--modules", required=True, type=str, nargs="+", help='Modules')
    parser.add_argument("-o", "--outdir", type=str, help='Output directory', default=".")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("-l", "--lang", type=str,
                        help='Output language (cpp=C++, go=Golang, js=JavaScript, md=Markdown)')
    action.add_argument("--print-version", action="store_true",
                        help='Print each module\'s protocol version, one per line in --modules order, '
                             'and generate nothing')
    parser.add_argument("-D", "--define", action='append', help="Define variables in 'key=value' format")

    args = parser.parse_args()

    try:
        # Parse variables
        variables = {}
        if args.define:
            for v in args.define:
                p = v.split("=")
                if len(p) != 2:
                    raise Exception("Invalid argument in -D option, must be 'key=value'")
                variables[p[0]] = p[1]

        modules_map = load_modules(args.basedirs, args.modules)

        data_types_preprocessor = DataTypesPreprocessor(PLAIN_TYPES, SPECIAL_TYPES)
        data_types_map = data_types_preprocessor.create_types_map(modules_map)

        # The hash covers the fields the preprocessor adds to each module, so this cannot skip it.
        # Every module is checked before anything is printed: a caller reading the lines by
        # position must not get a partial list that it could mistake for the whole.
        if args.print_version:
            for module_name, module in modules_map.items():
                if not module[GENERATE_PROTOCOL_VERSION]:
                    raise MessgenException("Module %s sets %s: false, so it has no version" %
                                           (module_name, GENERATE_PROTOCOL_VERSION))
            for module in modules_map.values():
                print(VersionProtocol(module).generate())
            return

        g_type = generators.get(args.lang)
        if g_type is None:
            raise MessgenException("Unsupported language \"%s\"" % args.lang)

        g = g_type(modules_map, data_types_map, MODULE_SEP, variables)
        g.generate(args.outdir)
        print("Successfully generated to %s" % args.outdir)
    except MessgenException as e:
        print("ERROR: %s" % e)
        exit(-1)


if __name__ == "__main__":
    main()
    
    
