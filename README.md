![JS CI](https://github.com/pavletto/messgen/actions/workflows/js.yml/badge.svg)
![CPP CI](https://github.com/pavletto/messgen/actions/workflows/cpp.yml/badge.svg)

# THE PROJECT IS MOVED

This repository contains old version of messgen, "v0", that is discontinued.
New version (v1), that is better adapted for usage for high frequency trading (while still can be used on embedded systems) moved to [github.com/Alber-Blanc/messgen](https://github.com/Alber-Blanc/messgen).

# Messgen

Lightweight and fast message serialization library.
Generates message classes/structs from yml scheme.

Features:

- Embedded-friendly
- Fixed size arrays
- Dynamic size arrays
- Nested messages
- Messages metadata
- Supported languages: C++, Go, JavaScript

## Dependencies

- python 3.X

On Linux:

```
sudo apt install python3
```

On Windows 10:

1. Download https://bootstrap.pypa.io/get-pip.py
2. Execute `python3 get_pip.py`
3. Execute `pip3 install pyyaml`

## Generate messages

Each protocol should be placed in directory `base_dir/vendor/protocol`.
`base_dir` is base directory for message definitions (is allowed to specify multiple base directories).
`vendor` is protocol vendor, it is used as namespace in generated messages allowing to avoid conflict between protocols from different vendors if used in one application.
`protocol` is protocol name, each protocol has protocol ID, that allows to use multiple protocols on single connection, e.g. bootloader and application protocols.

The protocol directory holds a `_protocol.yaml` describing the protocol itself:

```yaml
proto_id: 1
generate_protocol_version: true   # optional, defaults to true
```

`generate_protocol_version` controls the version stamp - an md5 over the protocol's own message set,
truncated to six hex digits - that C++, JSON and Markdown outputs carry (`PROTO_VERSION` and
`ProtoInfo::VERSION`, `version.json`, the `Version` line). Set it to false where the peers agree on
their wire format by other means, such as a hand-written constant or a copied message-id registry:
the hash covers field names, so a pure rename moves the stamp even though no byte on the wire moves,
and a stamp nobody checks reads as a protocol event to everyone who greps for it. Stating the default
explicitly does not move the stamp - the key is excluded from the hash.

Message generator usage:
```
python3 generate.py -b <base_dir> -m <vendor>/<protocol> -l <lang> -o <out_dir> [-D variable=value]
```

For some languages it's necessary to specify some variables using `-D` option.

Generated messages placed in `out_dir` directory.

#### Go

Example for Go messages generation:

```
python3 generate.py -b ./base_dir -m my_vendor/my_protocol -l go -o out/go -D messgen_go_module=example.com/path/to/messgen
```

Variable `messgen_go_module` must point to messgen Go module (`port/go/messgen`), to add necessary imports in generated messages.

#### C++

Example for C++ messages generation:

```
python3 generate.py -b ./base_dir -m my_vendor/my_protocol -l cpp -o out/cpp
```

Variable `metadata_json=true` can be passed to generate metadata in JSON format, rather than legacy.

#### JS/TS

Example for JS messages generation:

```
python3 generate.py -b ./base_dir -m my_vendor/my_protocol -l json -o out/json
```
This command will generate json messages. 

The types of these messages for TS can be generated as follows:

```
python3 generate.py -b ./base_dir -m my_vendor/my_protocol -l ts -o out/ts
```

if it is necessary to generate typed arrays for TS, it is necessary to pass the flag `-D typed_arrays=true`:
```
python3 generate.py -b ./base_dir -m my_vendor/my_protocol -l ts -o out/ts -D typed_arrays=true
```



#### MD

Example for protocol documentation generation:

```
python3 generate.py -b ./base_dir -m my_vendor/my_protocol -l md -o out/md
```
