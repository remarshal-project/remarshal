# Remarshal

[![PyPI package version badge.](https://img.shields.io/pypi/v/remarshal)](https://pypi.org/project/remarshal/)
![Python 3.12, 3.13, 3.14 supported.](https://img.shields.io/badge/python-3.12_%7C_3.13_%7C_3.14-blue)
[![PyPI download statistics badge.](https://img.shields.io/pypi/dm/remarshal)](https://pypistats.org/packages/remarshal)

Convert between CBOR, JSON, MessagePack, TOML, and YAML.
Convert all to Python code.

When installed, Remarshal provides the command `remarshal` as well as short commands like `yaml2json`.
These commands can be used to convert between formats, reformat, and detect errors as well as to transform data [with Starlark](#starlark-transformations).

## Known limitations and quirks

### YAML versions

Remarshal works with YAML 1.2 by default.
You can use the format `yaml-1.1` to work with YAML 1.1.
The format `yaml-1.2` can be used to select YAML 1.2 explicitly.
Conversion between YAML 1.1 and 1.2 is supported.

### Lossless by default; lossy must be enabled

Remarshal tries to convert documents without losing information by default.
This means that a document converted from format A to B and then back to A should be equal to the original document.
When a lossless conversion is impossible,
Remarshal exits with an error.

Use the option `-k`/`--stringify` to relax this restriction.
It will make Remarshal do the following:

- When converting to JSON, turn boolean and null keys and date-time keys and values into strings.
- When converting to TOML, turn boolean, date-time, and null keys and null values into strings.

This is **usually what you want**.
It isn't the default as a safeguard against information loss.

### Comments are removed

Remarshal does not preserve or convert TOML and YAML comments.

### Date-time conversion limitations

There are limitations on what data can be converted between formats.

- CBOR, MessagePack, and YAML with binary fields cannot be converted to JSON or TOML.
  Binary fields can be converted between CBOR, MessagePack, and YAML.
- The following date-time value conversions are possible:
  - Local dates are converted between [CBOR RFC 8943](https://www.rfc-editor.org/rfc/rfc8943.html) dates (tag 1004), [TOML Local Dates](https://toml.io/en/v1.1.0#local-date), and [YAML timestamps](https://yaml.org/spec/1.2.2/#tags) without a time or a time zone.
  - Local date-time is converted between [TOML Local Date-Time](https://toml.io/en/v1.1.0#local-date-time) and [YAML timestamps](https://yaml.org/spec/1.2.2/#tags) without a time zone.
  - Date-time with a time zone is converted between [CBOR standard date-time strings](https://www.rfc-editor.org/rfc/rfc8949.html#stringdatetimesect) (tag 0), the [MessagePack Timestamp extension type](https://github.com/msgpack/msgpack/blob/master/spec.md#timestamp-extension-type), [TOML Offset Date-Times](https://toml.io/en/v1.1.0#offset-date-time), and [YAML timestamps](https://yaml.org/spec/1.2.2/#tags) with a time zone.
- [TOML Local Time](https://toml.io/en/v1.1.0#local-time)
  cannot be converted to a date-time in another format.
- All date-time types can be converted to JSON with the `-k`/`--stringify` option, which turns them into strings.
  Converting a document with a date-time type to JSON fails without this option.

### Python output

Conversion to Python code is one-way.

Python output is either from [`repr`](https://docs.python.org/3/library/functions.html#repr) (the default) or formatted by [`pprint.pformat`](https://docs.python.org/3/library/pprint.html#pprint.pformat) (when you pass the option `--indent`).
The default `repr` format ignores `-s`/`--sort-keys`.

The style of `pprint` may not match your project's coding style.
It is recommended to apply your preferred Python formatter to the output.

Python output does not include the necessary `import` statements.
You may need to add `import datetime` before the data, for example.

## Installation

You will need Python 3.12 or later.
Earlier versions of Python are not supported.

The recommended way to run Remarshal is to install the latest release [from PyPI](https://pypi.org/project/remarshal/) with [pipx](https://github.com/pypa/pipx) or [uv](https://github.com/astral-sh/uv).

```sh
pipx install remarshal
# or
uv tool install remarshal
```

Regular installation is not mandatory.
The command `pipx run remarshal [arg ...]` will download Remarshal and run it from a temporary location.
It will cache the downloaded version for up to 14 days.
Remarshal will not be automatically upgraded during this period.
You can use `uvx remarshal [arg ...]` the same way.

It is also possible to install the current development version of Remarshal.
Prefer releases unless you have a reason to run a development version.

```sh
pipx install git+https://github.com/remarshal-project/remarshal
# or
uv tool install git+https://github.com/remarshal-project/remarshal
```

## Usage

<!-- USAGE -->
```none
usage: remarshal [-h] [-v]
                 [-f {cbor,json,msgpack,toml,yaml,yaml-1.1,yaml-1.2}]
                 [-i <input>] [--indent <n>] [-k] [--max-values <n>]
                 [--multiline <n>] [-o <output>] [-s]
                 [--starlark <code> | --starlark-file <path>]
                 [--starlark-max-allocs <n>] [--starlark-max-steps <n>]
                 [-t {cbor,json,msgpack,python,toml,yaml,yaml-1.1,yaml-1.2}]
                 [--unwrap <key>] [--verbose] [--width <n>] [--wrap <key>]
                 [--yaml-expand-aliases] [--yaml-style {,',",|,>}]
                 [--yaml-style-newline {,',",|,>}] [--yaml-tags]
                 [input] [output]

Convert between CBOR, JSON, MessagePack, TOML, and YAML.

positional arguments:
  input                 input file
  output                output file

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -f, --from, --if, --input-format 
{cbor,json,msgpack,toml,yaml,yaml-1.1,yaml-1.2}
                        input format
  -i, --input <input>   input file
  --indent <n>          JSON and YAML indentation
  -k, --stringify       turn into strings: boolean and null keys and date-time
                        keys and values for JSON; boolean, date-time, and null
                        keys and null values for TOML
  --max-values <n>      maximum number of values in input data (default
                        1000000, negative for unlimited)
  --multiline <n>       minimum number of items to make non-nested TOML array
                        multiline (default 6)
  -o, --output <output>
                        output file
  -s, --sort-keys       sort JSON, Python, and TOML keys instead of preserving
                        key order
  --starlark <code>     transform the data with a Starlark expression or
                        program; the input is bound to 'data'; the program
                        must assign the output to 'result'
  --starlark-file <path>
                        read a Starlark program from a file
  --starlark-max-allocs <n>
                        maximum cumulative bytes of Starlark allocations
                        (default 128 * 1048576, negative for unlimited)
  --starlark-max-steps <n>
                        maximum number of Starlark interpreter steps (default
                        10000000, negative for unlimited)
  -t, --to, --of, --output-format 
{cbor,json,msgpack,python,toml,yaml,yaml-1.1,yaml-1.2}
                        output format
  --unwrap <key>        only output the data stored under the given key
  --verbose             print debug information when an error occurs
  --width <n>           Python line width and YAML line width for long strings
                        (integer or 'inf')
  --wrap <key>          wrap the data in a map type with the given key
  --yaml-expand-aliases
                        expand YAML aliases (disable anchor/alias generation)
  --yaml-style {,',",|,>}
                        YAML formatting style
  --yaml-style-newline {,',",|,>}
                        YAML formatting style override for strings that
                        contain a newline
  --yaml-tags           translate between YAML tags and single-key mappings
                        with the tag as key (for example, '!secret foo' and
                        {'!secret': 'foo'}) so tags survive conversion to and
                        from other formats
```
<!-- END USAGE -->

Instead of `remarshal` with format arguments, you can use a short command like <code>{cbor,json,msgpack,toml,yaml}2<wbr>{cbor,json,msgpack,py,toml,yaml}</code>.
The `remarshal` command and the short commands exit with status 0 on success, 1 on operational failure, and 2 on failure to parse the command line.

If no input argument `input`/`-i input` is given or its value is `-`, Remarshal reads input data from standard input.
Similarly, with no `output`/`-o output` or an output argument that is `-`, Remarshal writes the result to standard output.

### Wrappers

The options `--wrap` and `--unwrap` are available to solve the problem of converting data to TOML from CBOR, JSON, MessagePack, or YAML when the top-level element of the data is not a dictionary (i.e., not a map in CBOR and MessagePack, an object in JSON, or a mapping in YAML).
Such data cannot be represented as TOML directly and must be wrapped in a dictionary first.

Passing the option `--wrap some-key` to `remarshal` or one of its short commands wraps the input data in a "wrapper" dictionary with one key, `some-key`, with the input data as its value.

The option `--unwrap some-key` does the opposite: it converts to the target format and outputs only the value stored under the key `some-key` in the top-level dictionary element of the input data; the rest of the input is discarded.
If the top-level element is not a dictionary or does not have the key `some-key`, `--unwrap some-key` causes an error.

The following shell transcript demonstrates the problem and how `--wrap` and `--unwrap` solve it:

```sh
$ echo '[{"a":"b"},{"c":[1,2,3]}]' | remarshal --from json --to toml
Error: cannot convert non-dictionary data to TOML; use "--wrap" to wrap it in a dictionary

$ echo '[{"a":"b"},{"c":[1,2,3]}]' \
  | remarshal --from json --to toml --wrap main
[[main]]
a = "b"

[[main]]
c = [1, 2, 3]

$ echo '[{"a":"b"},{"c":[1,2,3]}]' \
  | remarshal --from json --wrap main - test.toml

$ remarshal test.toml --to json
{"main":[{"a":"b"},{"c":[1,2,3]}]}

$ remarshal test.toml --to json --unwrap main
[{"a":"b"},{"c":[1,2,3]}]
```

### YAML tags

YAML lets you annotate a value with a [tag](https://yaml.org/spec/1.2.2/#3212-tags) such as `!secret`, which tools like [Home Assistant](https://www.home-assistant.io/docs/configuration/secrets/) give a special meaning.
No other format Remarshal supports has a native concept of tags.
By default, a tag in YAML input causes an error when you try to convert it to another format.

The option `--yaml-tags` exists to work around this.
It represents a YAML tag as a single-key mapping with the tag as the key.
For example, the YAML string value `!secret db_password` becomes the JSON object `{"!secret": "db_password"}` and vice versa.
For Remarshal to treat a mapping as a tag, it must have exactly one key that must start with `!`.

You can use this to generate tagged YAML from data in another format:

```sh
$ echo '{"!my-tag": {"foo": "bar", "baz": 123}}' \
  | remarshal --from json --to yaml --yaml-tags
!my-tag
foo: bar
baz: 123

$ echo '{"password": {"!secret": "db_password"}}' \
  | remarshal --from json --to yaml --yaml-tags
password: !secret db_password
```

It also works in the other direction.
Tags survive a round trip through a format with no tags:

```sh
$ printf 'name: !secret pw\nport: 8123\n' \
  | remarshal --from yaml --to json --yaml-tags
{"name":{"!secret":"pw"},"port":8123}
```

Without the option `--yaml-tags`, Remarshal still preserves tags when converting from YAML to YAML.

### Starlark transformations

You can transform the data between decoding and encoding using a Starlark expression or program.
[Starlark](https://laurent.le-brun.eu/blog/an-overview-of-starlark) is a small, sandboxed Python-like language with no filesystem, network, or subprocess access.

Pass Starlark code to Remarshal with `--starlark` or use `--starlark-file` to read it from a file.
The two options are mutually exclusive.
The decoded input is bound to the name `data`.

If the argument to `--starlark` parses as a single Starlark expression, the value of the expression becomes the new document.
Otherwise, the argument is treated as a program.
A Starlark program in Remarshal must assign the new document to the top-level name `result`.
A `--starlark-file` is always treated as a program.

```sh
$ echo '{"users":[{"name":"Alice","active":true},{"name":"Bob","active":false}]}' \
  | remarshal -f json -t yaml \
      --starlark '[user["name"] for user in data["users"] if user["active"]]'
- Alice
```

```sh
$ echo '{"a":1,"b":2,"c":3}' \
  | remarshal -f json -t json \
      --starlark 'x = sum(data.values()); result = {"sum": x, "values": data}'
{"sum":6,"values":{"a":1,"b":2,"c":3}}
```

#### Type mapping

Starlark has no `bytes` type and no date-time types.
Remarshal passes those values through opaquely and provides helper functions for inspecting and rebuilding them.
The other types map as follows.

| Remarshal value | Inside Starlark | Notes |
| --- | --- | --- |
| `int` | Same | [Starlark in Python](https://github.com/dbohdan/starlark-python) caps `int` at 2<sup>19</sup> bits (64 KiB or ≈158k decimal digits). |
| `None`, `bool`, `float`, `str` | Same | &mdash; |
| `bytes` | Opaque (no methods, not iterable) | Use `remarshal.bytes_to_str`, `remarshal.str_to_bytes`, `remarshal.bytes_len`, `remarshal.bytes_to_base64`, `remarshal.base64_to_bytes` |
| Date, time, date-time | Opaque | Use `remarshal.datetime_to_iso`, `remarshal.iso_to_datetime`, `remarshal.iso_to_date`, `remarshal.iso_to_time` |
| Dictionary (mapping) | `dict` | Insertion order is preserved |
| List (sequence) | `list` | &mdash; |

A `tuple` or a `range` returned by Starlark is converted to a list.
A `set` returned by Starlark causes an error; convert it explicitly with `sorted()` or `list()` first.

The standard Starlark `json` module is available with `json.encode()`, `json.decode()`, `json.encode_indent()`, and `json.indent()`.

#### Resource limits

By default, Starlark transformations limit CPU at 10&nbsp;000&nbsp;000 interpreter steps (`--starlark-max-steps`) and memory at 128 MiB of cumulative allocations (`--starlark-max-allocs`).
Pass a negative number for either option to disable that limit.
The output of a Starlark transform is also re-checked against `--max-values`.

## Shell completions

Remarshal provides shell-completion files for Bash and fish in the directory [`completions/`](completions/).
You can install fish completions automatically by running `install.fish`.
You will need to install Bash completions manually.

## Examples

### TOML to YAML

```sh
$ remarshal example.toml --to yaml
title: TOML Example
owner:
  name: Tom Preston-Werner
  organization: GitHub
  bio: "GitHub Cofounder & CEO\nLikes tater tots and beer."
  dob: 1979-05-27 07:32:00+00:00
database:
  server: 192.168.1.1
  ports:
  - 8001
  - 8001
  - 8002
  connection_max: 5000
  enabled: true
servers:
  alpha:
    ip: 10.0.0.1
    dc: eqdc10
  beta:
    ip: 10.0.0.2
    dc: eqdc10
    country: 中国
clients:
  data:
  - - gamma
    - delta
  - - 1
    - 2
  hosts:
  - alpha
  - omega
products:
- name: Hammer
  sku: 738594937
- name: Nail
  sku: 284758393
  color: gray
```

### JSON to TOML

```sh
$ curl -f 'https://archive-api.open-meteo.com/v1/era5?latitude=50.43&longitude=30.52&start_date=2014-10-05&end_date=2014-10-05&hourly=temperature_2m' \
  | remarshal --from json --to toml
latitude = 50.439365
longitude = 30.476192
generationtime_ms = 0.03254413604736328
utc_offset_seconds = 0
timezone = "GMT"
timezone_abbreviation = "GMT"
elevation = 147.0

[hourly_units]
time = "iso8601"
temperature_2m = "°C"

[hourly]
time = [
    "2014-10-05T00:00",
    "2014-10-05T01:00",
    "2014-10-05T02:00",
    "2014-10-05T03:00",
    "2014-10-05T04:00",
    "2014-10-05T05:00",
    "2014-10-05T06:00",
    "2014-10-05T07:00",
    "2014-10-05T08:00",
    "2014-10-05T09:00",
    "2014-10-05T10:00",
    "2014-10-05T11:00",
    "2014-10-05T12:00",
    "2014-10-05T13:00",
    "2014-10-05T14:00",
    "2014-10-05T15:00",
    "2014-10-05T16:00",
    "2014-10-05T17:00",
    "2014-10-05T18:00",
    "2014-10-05T19:00",
    "2014-10-05T20:00",
    "2014-10-05T21:00",
    "2014-10-05T22:00",
    "2014-10-05T23:00",
]
temperature_2m = [
    5.7,
    5.3,
    5.0,
    4.8,
    4.6,
    4.6,
    7.0,
    8.9,
    10.8,
    12.2,
    13.3,
    13.9,
    13.9,
    13.7,
    13.3,
    12.3,
    11.1,
    10.2,
    9.4,
    8.5,
    8.2,
    7.9,
    8.0,
    7.8,
]
```

Remarshal controls the number of items at which a TOML array becomes multiline, but it does not control the line width.
You can use [`taplo fmt`](https://taplo.tamasfe.dev/cli/usage/formatting.html) for finer TOML formatting.

## Versioning

Remarshal is primarily an application.
As an application, Remarshal follows [semantic versioning](https://semver.org/) for its command-line interface.
You can use it as a library at your own risk.
If you do, pin the minor version (for example, `remarshal>=2.1,<2.2`) so a future minor release does not break the Python API.

Dropping support for an old Python version is not considered a breaking change and doesn't bump the major version.
Python versions will be dropped some time after they reach their end of support.

## License

MIT.
See the file [`LICENSE`](LICENSE).

`example.toml` from <https://github.com/toml-lang/toml>.
`example.cbor`, `example.json`, `example.msgpack`, `example.py`, `example.yml`, `tests/bin.msgpack`, and `tests/bin.yml` are derived from it.
