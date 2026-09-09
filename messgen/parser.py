import os

import yaml

from .messgen_ex import MessgenException

CONFIG_EXT = ".yaml"
PROTOCOL_FILE = "_protocol" + CONFIG_EXT
CONSTANTS_FILE = "_constants" + CONFIG_EXT
EXISTING_TYPES_FILE = "_types" + CONFIG_EXT

# Opt-out key in PROTOCOL_FILE. A protocol whose peers agree on their wire format by some other
# means - a hand-written constant, a copied message-id registry - gets no use out of the generated
# stamp, and pays for it: the hash covers field names, so a rename reads as a protocol event to
# everyone who greps for the version. Setting it false drops the stamp from every generator.
GENERATE_PROTOCOL_VERSION = "generate_protocol_version"


def load_modules(basedirs, modules):
    modules_map = {}

    for module_name in modules:
        module_messages = []
        module_constants = []
        module_existing_types = []
        # Per module: a module whose PROTOCOL_FILE is missing must fail rather than inherit the
        # proto_id of the module parsed before it.
        proto_id = None
        generate_protocol_version = True
        paths_checked = []
        for basedir in basedirs:
            module_path = basedir + os.path.sep + module_name
            paths_checked.append(module_path)

            if os.path.exists(module_path):
                for item in os.listdir(module_path):
                    msg_file_path = module_path + os.path.sep + item

                    if not (os.path.isfile(msg_file_path) and item.endswith(CONFIG_EXT)):
                        continue

                    msg_name = item.replace(CONFIG_EXT, "")

                    with open(msg_file_path, "r") as f:
                        msg = yaml.safe_load(f)

                        if item == PROTOCOL_FILE:
                            if msg.get("proto_id") is None:
                                raise MessgenException("Missing proto id field")

                            proto_id = msg["proto_id"]
                            generate_protocol_version = msg.get(GENERATE_PROTOCOL_VERSION, True)

                            if not isinstance(generate_protocol_version, bool):
                                raise MessgenException(
                                    "%s must be true or false in %s, got '%s'" %
                                    (GENERATE_PROTOCOL_VERSION, msg_file_path, generate_protocol_version))

                            for existing_mod_name, existing_mod in modules_map.items():
                                if existing_mod["proto_id"] == proto_id:
                                    raise MessgenException(
                                        "Duplicate proto_id=%s in modules '%s' and '%s'" %
                                        (proto_id, module_name, existing_mod_name))

                            continue

                        if item == CONSTANTS_FILE:
                            if msg is not None:
                                module_constants = msg

                            continue

                        if item == EXISTING_TYPES_FILE:
                            if msg is not None:
                                module_existing_types = msg

                            continue

                        if (msg is None) or (msg.get("id") is None):
                            raise MessgenException("Wrong message file format in %s" % msg_file_path)

                        msg["name"] = msg_name

                        for m in module_messages:
                            if m["id"] == msg["id"]:
                                raise MessgenException(
                                    "Duplicate ID=%s for messages '%s' and '%s' in module %s"
                                    % (m["id"], m["name"], msg["name"], module_name))
                        module_messages.append(msg)

        if proto_id == None:
            raise MessgenException("No messages found for module %s. Paths checked: %s" % (module_name, paths_checked))

        modules_map[module_name] = {
            "proto_id": proto_id,
            GENERATE_PROTOCOL_VERSION: generate_protocol_version,
            "constants": module_constants,
            "existing_types": module_existing_types,
            "messages": list(
                sorted(module_messages,
                       key=lambda msg: msg["id"])
            )
        }

    return modules_map
