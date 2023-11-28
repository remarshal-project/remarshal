# Remarshal

Convert between CBOR, JSON, MessagePack, TOML, and YAML.
When installed, provides the command-line command `remarshal` as well as the short commands <code>{cbor,json,msgpack,toml,yaml}2<wbr>{cbor,json,msgpack,toml,yaml}</code>.
You can perform format conversion, reformatting, and error detection using these commands.

## Known limitations

* CBOR, MessagePack, and YAML with binary fields cannot be converted to JSON or TOML.
Binary fields are converted between CBOR, MessagePack, and YAML.
* TOML containing values of the [Local Date-Time](https://toml.io/en/v1.0.0-rc.1#local-date-time) type cannot be converted to CBOR.
The Local Date type can only be converted to JSON and YAML.
The Local Time type cannot be converted to any other format.
Offset Date-Time and its equivalents can be converted between CBOR, MessagePack, TOML, and YAML.
Keys of any date-time type are converted to string TOML keys.
* Date and time types are converted to JSON strings.
They cannot be safely roundtripped through JSON.
* A YAML timestamp with only a date becomes a YAML timestamp or a TOML Local Date-Time for the midnight of that date.
This means you cannot roundtrip every YAML document through Remarshal.

## Installation

You will need Python 3.8 or later.
Earlier versions of Python 3 do not work.

The recommended way to run Remarshal is to install the latest release [from PyPI](https://pypi.org/project/remarshal/) with [pipx](https://github.com/pypa/pipx).

```sh
pipx install remarshal
```

Regular installation is not mandatory.
The command

```sh
pipx run remarshal [arg ...]
```

will download Remarshal and run it from a temporary location.
It will cache the downloaded version for up to 14 days.
Remarshal will not be automatically upgraded during this period.

You can install Remarshal using pip.

```sh
python3 -m pip install --user remarshal
```

It is possible to install the current development version instead of a release.
Prefer releases unless you have a reason to run the development version.

```sh
pipx install git+https://github.com/remarshal-project/remarshal
```

## Usage

```
usage: remarshal [-h] [-v] [-i <input>] [--if {cbor,json,msgpack,toml,yaml}]
                 [--json-indent <n>] [-k] [--max-values <n>] [-o <output>]
                 [--of {cbor,json,msgpack,toml,yaml}] [-s] [--unwrap <key>]
                 [--verbose] [--wrap <key>] [--yaml-indent <n>]
                 [--yaml-style {,',",|,>}] [--yaml-width <n>]
                 [input] [output]

Convert between CBOR, JSON, MessagePack, TOML, and YAML.

positional arguments:
  input                 input file
  output                output file

options:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -i <input>, --input <input>
                        input file
  --if {cbor,json,msgpack,toml,yaml}, --input-format
{cbor,json,msgpack,toml,yaml}, -f {cbor,json,msgpack,toml,yaml},
--from {cbor,json,msgpack,toml,yaml}
                        input format
  --json-indent <n>     JSON indentation
  -k, --stringify       turn into strings boolean, date-time, and null keys
                        for JSON and TOML and null values for TOML
  --max-values <n>      maximum number of values in input data (default
                        1000000, negative for unlimited)
  -o <output>, --output <output>
                        output file
  --of {cbor,json,msgpack,toml,yaml}, --output-format
{cbor,json,msgpack,toml,yaml}, -t {cbor,json,msgpack,toml,yaml},
--to {cbor,json,msgpack,toml,yaml}
                        output format
  -s, --sort-keys       sort JSON, TOML, YAML keys instead of preserving key
                        order
  --unwrap <key>        only output the data stored under the given key
  --verbose             print debug information when an error occurs
  --wrap <key>          wrap the data in a map type with the given key
  --yaml-indent <n>     YAML indentation
  --yaml-style {,',",|,>}
                        YAML formatting style
  --yaml-width <n>      YAML line width for long strings
```

Instead of `remarshal` with format arguments,
you can use a short command <code>{cbor,json,msgpack,toml,yaml}2<wbr>{cbor,json,msgpack,toml,yaml}</code>.
The `remarshal` command as well as the short commands exit with status 0 on success, 1 on operational failure, and 2 when they fail to parse the command line.

If no input argument `input`/`-i input` is given or its value is `-`, Remarshal reads input data from standard input.
Similarly, with no `output`/`-o output` or an output argument that is `-`, it writes the result to standard output.

### Wrappers

The arguments `--wrap` and `--unwrap` are available to solve the problem of converting CBOR, JSON, MessagePack, and YAML data to TOML if the top-level element of the data is not of a dictionary type
(i.e., not a map in CBOR and MessagePack, an object in JSON, or an associative array in YAML).
You cannot represent such data as TOML directly;
the data must be wrapped in a dictionary first.
Passing the flag `--wrap some-key` to `remarshal` or one of its short commands wraps the input data in a "wrapper" dictionary with one key, `some-key`, with the input data as its value.
The flag `--unwrap some-key` does the opposite:
only the value stored under the key `some-key` in the top-level dictionary element of the input data is converted to the target format and output;
the rest of the input is ignored.
If the top-level element is not a dictionary or does not have the key `some-key`,
`--unwrap some-key` causes an error.

The following shell transcript demonstrates the problem and how `--wrap` and `--unwrap` solve it:

```
$ echo '[{"a":"b"},{"c":[1,2,3]}]' | remarshal --if json --of toml
Error: cannot convert non-dictionary data to TOML; use "--wrap" to wrap it in a dictionary

$ echo '[{"a":"b"},{"c":[1,2,3]}]' \
  | remarshal --if json --of toml --wrap main
[[main]]
a = "b"

[[main]]
c = [1, 2, 3]

$ echo '[{"a":"b"},{"c":[1,2,3]}]' \
  | remarshal --if json --wrap main - test.toml

$ remarshal test.toml --of json
{"main":[{"a":"b"},{"c":[1,2,3]}]}

$ remarshal test.toml --of json --unwrap main
[{"a":"b"},{"c":[1,2,3]}]
```

## Examples

```
$ remarshal example.toml --of yaml
clients:
  data:
  - - gamma
    - delta
  - - 1
    - 2
  hosts:
  - alpha
  - omega
database:
  connection_max: 5000
  enabled: true
  ports:
  - 8001
  - 8001
  - 8002
  server: 192.168.1.1
owner:
  bio: 'GitHub Cofounder & CEO

    Likes tater tots and beer.'
  dob: 1979-05-27 07:32:00+00:00
  name: Tom Preston-Werner
  organization: GitHub
products:
- name: Hammer
  sku: 738594937
- color: gray
  name: Nail
  sku: 284758393
servers:
  alpha:
    dc: eqdc10
    ip: 10.0.0.1
  beta:
    country: 中国
    dc: eqdc10
    ip: 10.0.0.2
title: TOML Example

$ curl -s 'http://api.openweathermap.org/data/2.5/weather?q=Kiev,ua' \
  | remarshal --if json --of toml
base = "cmc stations"
cod = 200
dt = 1412532000
id = 703448
name = "Kiev"

[clouds]
all = 44

[coord]
lat = 50.42999999999999972
lon = 30.51999999999999957

[main]
humidity = 66
pressure = 1026
temp = 283.49000000000000909
temp_max = 284.14999999999997726
temp_min = 283.14999999999997726

[sys]
country = "UA"
id = 7358
message = 0.24370000000000000
sunrise = 1412481902
sunset = 1412522846
type = 1

[[weather]]
description = "scattered clouds"
icon = "03n"
id = 802
main = "Clouds"

[wind]
deg = 80
speed = 2
```

## License

MIT. See the file `LICENSE`.

`example.toml` from <https://github.com/toml-lang/toml>. `example.json`, `example.msgpack`, `example.cbor`, `example.yml`, `tests/bin.msgpack`, and `tests/bin.yml` are derived from it.
