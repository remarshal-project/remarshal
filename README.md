# Remarshal

Convert between CBOR, JSON, MessagePack, TOML, and YAML.
When installed, Remarshal provides the command-line command `remarshal` as well as short commands like `yaml2json`.
You can use these commands to convert between formats, reformat, and detect errors.

Remarshal can also convert all supported formats to Python code.

## Known limitations and quirks

### YAML versions

Remarshal works with YAML 1.2 by default.
You can use the format `yaml-1.1` to work with YAML 1.1.
The format `yaml-1.2` can be used to be explicit about using YAML 1.2.
Conversion between YAML 1.1 and 1.2 is supported.

### Lossless by default; lossy must be enabled

Remarshal tries to convert documents without losing information by default.
This means that a document converted from format A to B and then back to A should be equal to the original document.
When a lossless conversion is impossible,
Remarshal exits with an error.

Use the command-line option `-k`/`--stringify` to relax this restriction.
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

To enable [Starlark transforms](#starlark-transforms), add the `[starlark]` extra:

```sh
pipx install 'remarshal[starlark]'
# or
uv tool install 'remarshal[starlark]'
```

## Usage

<!-- USAGE -->
```none
usage: remarshal [-h] [-v] [--expand-aliases]
                 [-f {cbor,json,msgpack,toml,yaml,yaml-1.1,yaml-1.2}]
                 [-i <input>] [--indent <n>] [-k] [--max-values <n>]
                 [--multiline <n>] [-o <output>] [-s]
                 [--starlark <code> | --starlark-file <path>]
                 [--starlark-max-allocs <n>] [--starlark-max-steps <n>]
                 [-t {cbor,json,msgpack,python,toml,yaml,yaml-1.1,yaml-1.2}]
                 [--unwrap <key>] [--verbose] [--width <n>] [--wrap <key>]
                 [--yaml-style {,',",|,>}] [--yaml-style-newline {,',",|,>}]
                 [input] [output]

Convert between CBOR, JSON, MessagePack, TOML, and YAML.

positional arguments:
  input                 input file
  output                output file

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  --expand-aliases      expand YAML aliases (disable anchor/alias generation)
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
  --yaml-style {,',",|,>}
                        YAML formatting style
  --yaml-style-newline {,',",|,>}
                        YAML formatting style override for strings that
                        contain a newline
```
<!-- END USAGE -->

Instead of `remarshal` with format arguments, you can use a short command like <code>{cbor,json,msgpack,toml,yaml}2<wbr>{cbor,json,msgpack,py,toml,yaml}</code>.
The `remarshal` command and the short commands exit with status 0 on success, 1 on operational failure, and 2 on failure to parse the command line.

If no input argument `input`/`-i input` is given or its value is `-`, Remarshal reads input data from standard input.
Similarly, with no `output`/`-o output` or an output argument that is `-`, Remarshal writes the result to standard output.

### Wrappers

The options `--wrap` and `--unwrap` are available to solve the problem of converting data to TOML from CBOR, JSON, MessagePack, or YAML when the top-level element of the data is not a dictionary (i.e., not a map in CBOR and MessagePack, an object in JSON, or an associative array in YAML).
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

### Starlark transforms

The optional `[starlark]` install extra lets you transform the data between decoding and encoding using a [Starlark](https://github.com/bazelbuild/starlark) expression or program.
Starlark is a small, sandboxed Python-like language with no filesystem, network, or subprocess access.
See [Installation](#installation) for how to enable it.

Pass code to Remarshal with `--starlark` or read it from a file with `--starlark-file`.
The two options are mutually exclusive.
The decoded input is bound to the name `data`.

If the argument to `--starlark` parses as a single Starlark expression, its value becomes the new document.
Otherwise, it is treated as a program that must assign the new document to a top-level name `result`.
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
| `None`, `bool`, `int`, `float`, `str` | the same | `int` is arbitrary precision |
| `bytes` | opaque (no methods, not iterable) | use `remarshal.bytes_decode`, `remarshal.bytes_encode`, `remarshal.bytes_len`, `remarshal.b64_encode`, `remarshal.b64_decode` |
| date, time, date-time | opaque | use `remarshal.datetime_isoformat`, `remarshal.datetime_parse`, `remarshal.date_parse`, `remarshal.time_parse` |
| dictionary (mapping) | `dict` | insertion order is preserved |
| list (sequence) | `list` |  |

A `tuple` or a `range` returned by Starlark is converted to a list.
A `set` returned by Starlark causes an error; convert it explicitly with `sorted(s)` or `list(s)` first.

The standard Starlark `json` module is available with `json.encode(x)`, `json.decode(s)`, `json.encode_indent(x)`, and `json.indent(s)`.

#### Resource limits

By default, Starlark transforms limit CPU at 10 000 000 interpreter steps (`--starlark-max-steps`) and memory at 128 MiB of cumulative allocations (`--starlark-max-allocs`).
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
If you do, pin the minor version (for example, `remarshal>=2.0,<2.1`) so a future minor release does not break the Python API.

Dropping support for an old Python version is not considered a breaking change and doesn't bump the major version.

## License

MIT.
See the file [`LICENSE`](LICENSE).

`example.toml` from <https://github.com/toml-lang/toml>.
`example.cbor`, `example.json`, `example.msgpack`, `example.py`, `example.yml`, `tests/bin.msgpack`, and `tests/bin.yml` are derived from it.
