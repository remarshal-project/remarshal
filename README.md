# Remarshal

Convert between CBOR, JSON, MessagePack, TOML, and YAML.
When installed,
Remarshal provides the command-line command `remarshal`
as well as the short commands
<code>{cbor,json,msgpack,toml,yaml}2<wbr>{cbor,json,msgpack,toml,yaml}</code>.
You can use these commands
to convert between formats,
reformat,
and detect errors.

Remarshal can also convert all supported formats to Python code.

## Known limitations and quirks

### YAML 1.2 only

Remarshal works with YAML 1.2.
The last version that read and wrote YAML 1.1 was 0.17.1.
Install it if you need YAML 1.1.

### Lossless by default; lossy must be enabled

Remarshal tries to convert documents without losing information by default.
This means that a document converted from format A to B and then back to A should be equal to the original document.
When a lossless conversion is impossible,
Remarshal exits with an error.

Use the command-line option `-k`/`--stringify` to relax this restriction.
It will make Remarshal do the following:

- When converting to JSON,   turn boolean and null keys and date-time keys and values into strings.
- When converting to TOML,
  turn boolean, date-time, and null keys and null values into strings.

This is **usually what you want**.
It isn't the default as a safeguard against information loss.

### Comments are removed

Remarshal does not preserve or convert TOML and YAML comments.

### Date-time conversion limitations

There are limitations
on what data can be converted
between what formats.

- CBOR, MessagePack, and YAML with binary fields cannot be converted
  to JSON or TOML.
  Binary fields can be converted between CBOR, MessagePack, and YAML.
- The following date-time value conversions are possible:
  - Local dates are converted between
    [CBOR RFC 8943](https://www.rfc-editor.org/rfc/rfc8943.html)
    dates (tag 1004),
    [TOML Local Dates](https://toml.io/en/v1.0.0#local-date),
    and
    [YAML timestamps](https://yaml.org/spec/1.2.2/#tags)
    without a time or a time zone.
  - Local date-time is converted between
    [TOML Local Date-Time](https://toml.io/en/v1.0.0#local-date-time)
    and
    [YAML timestamps](https://yaml.org/spec/1.2.2/#tags)
    without a time zone.
  - Date-time with a time zone
    is converted between
    [CBOR standard date-time strings](https://www.rfc-editor.org/rfc/rfc8949.html#stringdatetimesect)
    (tag 0),
    the
    [MessagePack Timestamp extension type](https://github.com/msgpack/msgpack/blob/master/spec.md#timestamp-extension-type),
    [TOML Offset Date-Times](https://toml.io/en/v1.0.0#offset-date-time),
    and
    [YAML timestamps](spec/1.2.2/#tags) with a time zone.
- [TOML Local Time](https://toml.io/en/v1.0.0#local-time)
  cannot be converted to a date-time in another format.
- All date-time types can be converted to JSON
  with the `-k`/`--stringify` option,
  which turns them into strings.
  Converting a document with a date-time type to JSON fails without `-k`/`--stringify`.
- Remarshal converts YAML dates to TOML Local Dates.
  It converts TOML Local Dates to YAML dates.

### Python output

Conversion to Python code is one-way.

The Python output is either from
[`repr`](https://docs.python.org/3/library/functions.html#repr)
(the default) or formatted by
[`pprint.pformat`](https://docs.python.org/3/library/pprint.html#pprint.pformat)
(when you pass the option `--indent`).
The style of `pprint`
is probably not what you want your Python code to look like.
Apply your preferred Python formatter to it.

The Python output does not include the necessary `import` statements.
You may need to add `import datetime` before the data.

## Installation

You will need Python 3.9 or later.
Earlier versions of Python 3 will not work.

The recommended way to run Remarshal is to install the latest release
[from PyPI](https://pypi.org/project/remarshal/)
with
[pipx](https://github.com/pypa/pipx)
or
[uv](https://github.com/astral-sh/uv).

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

You can install Remarshal for the current user with pip.
This isn't recommended because of the potential dependency version conflicts between Remarshal and other packages.

```sh
python3 -m pip install --user remarshal
```

It is also possible to install the current development version of Remarshal.
Prefer releases unless you have a reason to run a development version.

```sh
pipx install git+https://github.com/remarshal-project/remarshal
# or
uv tool install https://github.com/remarshal-project/remarshal
```

## Usage

```none
usage: remarshal [-h] [-v] [-f {cbor,json,msgpack,toml,yaml}] [-i <input>]
                 [--indent <n>] [-k] [--max-values <n>] [-o <output>] [-s]
                 [-t {cbor,json,msgpack,python,toml,yaml}] [--unwrap <key>]
                 [--verbose] [--width <n>] [--wrap <key>]
                 [--yaml-style {,',",|,>}]
                 [input] [output]

Convert between CBOR, JSON, MessagePack, TOML, and YAML.

positional arguments:
  input                 input file
  output                output file

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -f, --from, --if, --input-format {cbor,json,msgpack,toml,yaml}
                        input format
  -i, --input <input>   input file
  --indent <n>          JSON and YAML indentation
  -k, --stringify       turn into strings: boolean and null keys and date-time
                        keys and values for JSON; boolean, date-time, and null
                        keys and null values for TOML
  --max-values <n>      maximum number of values in input data (default
                        1000000, negative for unlimited)
  -o, --output <output>
                        output file
  -s, --sort-keys       sort JSON, Python, and TOML keys instead of preserving
                        key order
  -t, --to, --of, --output-format {cbor,json,msgpack,python,toml,yaml}
                        output format
  --unwrap <key>        only output the data stored under the given key
  --verbose             print debug information when an error occurs
  --width <n>           Python line width and YAML line width for long strings
                        (integer or 'inf')
  --wrap <key>          wrap the data in a map type with the given key
  --yaml-style {,',",|,>}
                        YAML formatting style
```

Instead of `remarshal` with format arguments,
you can use a short command
<code>{cbor,json,msgpack,toml,yaml}2<wbr>{cbor,json,msgpack,toml,yaml}</code>.
The `remarshal` command and the short commands
exit with status 0 on success,
1 on operational failure,
and 2 on failure to parse the command line.

If no input argument `input`/`-i input` is given or its value is `-`,
Remarshal reads input data from standard input.
Similarly,
with no `output`/`-o output` or an output argument that is `-`,
Remarshal writes the result to standard output.

### Wrappers

The options `--wrap` and `--unwrap` are available
to solve the problem of converting CBOR, JSON, MessagePack, and YAML data to TOML
when the top-level element of the data is not of a dictionary type
(i.e., not a map in CBOR and MessagePack,
an object in JSON,
or an associative array in YAML).
You cannot represent such data as TOML directly;
the data must be wrapped in a dictionary first.
Passing the option `--wrap some-key` to `remarshal` or one of its short commands
wraps the input data in a "wrapper" dictionary with one key, `some-key`,
with the input data as its value.
The option `--unwrap some-key` does the opposite:
it converts to the target format and outputs
only the value stored under the key `some-key`
in the top-level dictionary element of the input data;
the rest of the input is discarded.
If the top-level element is not a dictionary or does not have the key `some-key`,
`--unwrap some-key` causes an error.

The following shell transcript demonstrates the problem
and how `--wrap` and `--unwrap` solve it:

```
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

$ remarshal test.toml --of json --unwrap main
[{"a":"b"},{"c":[1,2,3]}]
```

## Examples

### TOML to YAML

```
$ remarshal example.toml --of yaml
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

```
$ curl -f 'https://archive-api.open-meteo.com/v1/era5?latitude=50.43&longitude=30.52&start_date=2014-10-05&end_date=2014-10-05&hourly=temperature_2m' \
  | remarshal --from json --to toml \
  ;
latitude = 50.439365
longitude = 30.476192
generationtime_ms = 0.04208087921142578
utc_offset_seconds = 0
timezone = "GMT"
timezone_abbreviation = "GMT"
elevation = 147.0

[hourly_units]
time = "iso8601"
temperature_2m = "°C"

[hourly]
time = ["2014-10-05T00:00", "2014-10-05T01:00", "2014-10-05T02:00", "2014-10-05T03:00", "2014-10-05T04:00", "2014-10-05T05:00", "2014-10-05T06:00", "2014-10-05T07:00", "2014-10-05T08:00", "2014-10-05T09:00", "2014-10-05T10:00", "2014-10-05T11:00", "2014-10-05T12:00", "2014-10-05T13:00", "2014-10-05T14:00", "2014-10-05T15:00", "2014-10-05T16:00", "2014-10-05T17:00", "2014-10-05T18:00", "2014-10-05T19:00", "2014-10-05T20:00", "2014-10-05T21:00", "2014-10-05T22:00", "2014-10-05T23:00"]
temperature_2m = [5.7, 5.3, 5.0, 4.8, 4.6, 4.6, 7.0, 8.9, 10.8, 12.2, 13.3, 13.9, 13.9, 13.7, 13.3, 12.3, 11.1, 10.2, 9.4, 8.5, 8.2, 7.9, 8.0, 7.8]
```

Remarshal does not limit the line length in TOML.
You can use
[`taplo fmt`](https://taplo.tamasfe.dev/cli/usage/formatting.html)
to reformat the TOML and break up long lines with arrays.

## License

MIT.
See the file
[`LICENSE`](LICENSE).

`example.toml` from <https://github.com/toml-lang/toml>.
`example.cbor`,
`example.json`,
`example.msgpack`,
`example.py`,
`example.yml`,
`tests/bin.msgpack`,
and `tests/bin.yml`
are derived from it.
