# Remarshal

Convert between CBOR, JSON, MessagePack, TOML, and YAML. When installed,
provides the command line command `remarshal` as well as the short commands
`{cbor,json,msgpack,toml,yaml}2`&#x200B;`{cbor,json,msgpack,toml,yaml}`. With
these commands, you can perform format conversion, reformatting, and error
detection.

## Known limitations

* CBOR, MessagePack, and YAML with binary fields can not be converted to JSON
or TOML. Binary fields are converted between CBOR, MessagePack, and YAML.
* TOML containing values of the
[Local Date-Time](https://toml.io/en/v1.0.0-rc.1#local-date-time) type can not
be converted to CBOR. The Local Date type can only be converted to JSON and
YAML. The Local Time type can not be converted to any other format. Offset
Date-Time and its equivalents can be converted between CBOR, MessagePack,
TOML, and YAML.
* Date and time types are converted to JSON strings. They can not be safely
roundtripped through JSON.
* A YAML timestamp with only a date becomes a TOML Local Date-Time for the
midnight of that date.

## Installation

You will need Python 3.8 or later. Earlier versions of Python 3 are not
supported.

The quickest way to run Remarshal is with
 [pipx](https://github.com/pypa/pipx).

```sh
pipx run remarshal
# or
pipx install remarshal
remarshal
```

You can install the latest release of Remarshal from PyPI using pip.

```sh
python3 -m pip install --user remarshal
```

Alternatively, you can install the development version. Prefer releases unless you have a reason to run the development version.

```sh
python3 -m pip install --user git+https://github.com/remarshal-project/remarshal
```

## Usage

```
usage: remarshal.py [-h] [-i input] [-o output]
                    [--if {cbor,json,msgpack,toml,yaml}]
                    [--of {cbor,json,msgpack,toml,yaml}]
                    [--json-indent n]
                    [--yaml-indent n]
                    [--yaml-style {,',",|,>}]
                    [--yaml-width n]
                    [--wrap key] [--unwrap key]
                    [--sort-keys] [-v]
                    [input] [output]
```

```
usage: {cbor,json,msgpack,toml,yaml}2cbor [-h] [-i input] [-o output]
                                          [--wrap key] [--unwrap key]
                                          [-v]
                                          [input] [output]
```

```
usage: {cbor,json,msgpack,toml,yaml}2json [-h] [-i input] [-o output]
                                          [--json-indent n]
                                          [--wrap key] [--unwrap key]
                                          [--sort-keys] [-v]
                                          [input] [output]
```

```
usage: {cbor,json,msgpack,toml,yaml}2msgpack [-h] [-i input] [-o output]
                                             [--wrap key] [--unwrap key]
                                             [-v]
                                             [input] [output]
```

```
usage: {cbor,json,msgpack,toml,yaml}2toml [-h] [-i input] [-o output]
                                          [--wrap key] [--unwrap key]
                                          [--sort-keys] [-v]
                                          [input] [output]
```

```
usage: {cbor,json,msgpack,toml,yaml}2yaml [-h] [-i input] [-o output]
                                          [--yaml-indent n]
                                          [--yaml-style {,',",|,>}]
                                          [--yaml-width n]
                                          [--wrap key] [--unwrap key]
                                          [--sort-keys] [-v]
                                          [input] [output]
```

All of the commands above exit with status 0 on success, 1 on operational
failure, and 2 when they fail to parse the command line.

If no input argument `input`/`-i input` is given or its value is `-`, Remarshal reads input data from standard input. Similarly,
with no `output`/`-o output` or an output argument that is `-`, it writes the result to standard output.

### Wrappers

The arguments `--wrap` and `--unwrap` are available to solve the problem of
converting CBOR, JSON, MessagePack, and YAML data to TOML if the top-level
element of the data is not of a dictionary type (i.e., not a map in CBOR and
MessagePack, an object in JSON, or an associative array in YAML).
You can not represent such data as TOML directly; the data must be wrapped in a
dictionary first. Passing the flag `--wrap someKey` to `remarshal` or one of
its short commands wraps the input data in a "wrapper" dictionary with one key,
"someKey", with the input data as its value. The flag `--unwrap someKey` does
the opposite: only the value stored under the key "someKey" in the top-level
dictionary element of the input data is converted to the target format and
output; the rest of the input is ignored. If the top-level element is not a
dictionary or does not have the key "someKey", `--unwrap someKey` causes an
error.

The following shell transcript demonstrates the problem and how `--wrap` and
`--unwrap` solve it:

```
$ echo '[{"a":"b"},{"c":[1,2,3]}]' | ./remarshal.py --if json --of toml
Error: cannot convert non-dictionary data to TOML; use "wrap" to wrap it in a dictionary

$ echo '[{"a":"b"},{"c":[1,2,3]}]' \
  | ./remarshal.py --if json --of toml --wrap main
[[main]]
a = "b"

[[main]]
c = [1, 2, 3]

$ echo '[{"a":"b"},{"c":[1,2,3]}]' \
  | ./remarshal.py --if json --wrap main - test.toml

$ ./remarshal.py test.toml --of json
{"main":[{"a":"b"},{"c":[1,2,3]}]}

$ ./remarshal.py test.toml --of json --unwrap main
[{"a":"b"},{"c":[1,2,3]}]
```

## Examples

```
$ ./remarshal.py example.toml --of yaml
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

$ curl -s http://api.openweathermap.org/data/2.5/weather\?q\=Kiev,ua \
  | ./remarshal.py --if json --of toml
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

`example.toml` from <https://github.com/toml-lang/toml>. `example.json`,
`example.msgpack`, `example.cbor`, `example.yml`, `tests/bin.msgpack`, and `tests/bin.yml` are derived from it.
