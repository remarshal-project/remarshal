# remarshal

[![Travis CI Build Status](https://travis-ci.org/dbohdan/remarshal.svg?branch=master)](https://travis-ci.org/dbohdan/remarshal)
[![AppVeyor CI Build Status](https://ci.appveyor.com/api/projects/status/github/dbohdan/remarshal?branch=master&svg=true)](https://ci.appveyor.com/project/dbohdan/remarshal)

Convert between JSON, MessagePack, TOML, YAML, and CBOR.  When installed,
provides the command line command `remarshal` as well as the short commands
`{json,msgpack,toml,yaml,cbor}2{json,msgpack,toml,yaml,cbor}`.  These commands
can be used for format conversion, reformatting, and error detection.

## Known limitations

* Remarshal currently only supports TOML 0.4.0.
* Binary fields (i.e., from MessagePack, YAML, or CBOR) can't be converted
to JSON or TOML
with the Python 3 version of remarshal.  They can be converted between each
other.  With Python 2 binary fields are coerced to strings.  This means that
with Python 2 `{msgpack,yaml,cbor}2*` is lossy.

## Installation

You will need Python 2.7 or Python 3.5 or later.  Earlier versions of Python 3
may work but are not supported.

You can install the latest release from PyPI using pip.

```sh
python3 -m pip install remarshal --user
```

Alternatively, clone the `master` branch to install the development version.

```sh
git clone https://github.com/dbohdan/remarshal
cd remarshal
python3 setup.py install --user
```

## Usage

```
usage: remarshal.py [-h] [-i input] [-o output]
                    [--if {json,msgpack,toml,yaml,cbor}]
                    [--of {json,msgpack,toml,yaml,cbor}]
                    [--indent-json n]
                    [--yaml-style {,',",|,>}]
                    [--wrap key] [--unwrap key]
                    [--preserve-key-order] [-v]
                    [input] [output]
```

```
usage: {json,msgpack,toml,yaml,cbor}2json [-h] [-i input] [-o output]
                                          [--indent-json n]
                                          [--wrap key] [--unwrap key]
                                          [--preserve-key-order] [-v]
                                          [input] [output]
```

```
usage: {json,msgpack,toml,yaml,cbor}2msgpack [-h] [-i input] [-o output]
                                             [--wrap key] [--unwrap key]
                                             [--preserve-key-order] [-v]
                                             [input] [output]
```

```
usage: {json,msgpack,toml,yaml,cbor}2toml [-h] [-i input] [-o output]
                                          [--wrap key] [--unwrap key]
                                          [--preserve-key-order] [-v]
                                          [input] [output]
```

```
usage: {json,msgpack,toml,yaml,cbor}2yaml [-h] [-i input] [-o output]
                                          [--yaml-style {,',",|,>}]
                                          [--wrap key] [--unwrap key]
                                          [--preserve-key-order] [-v]
                                          [input] [output]
```

```
usage: {json,msgpack,toml,yaml,cbor}2cbor [-h] [-i input] [-o output]
                                          [--wrap key] [--unwrap key]
                                          [--preserve-key-order] [-v]
                                          [input] [output]
```


All of the commands above exit with status 0 on success, 1 on operational
failure, and 2 when they fail to parse the command line.

If no input argument `input`/ `-i input` is given or its value is `-` or
a blank string the data to convert is read from the standard input.  Similarly,
with no `output`/`-o output` or an output argument that is `-` or a blank
string the result of the conversion is written to the standard output.

### Wrappers

The arguments `--wrap` and `--unwrap` are there to solve the problem of
converting JSON, MessagePack, and YAML data to TOML if the top-level element
of that data is not of a dictionary type (i.e., not an object in JSON, a map
in MessagePack, or an associative array in YAML) but a list, a string, or
a number.  Such data can not be represented as TOML directly; it needs to be
wrapped in a dictionary first.  Passing the flag `--wrap someKey` to
`remarshal` or one of its short commands wraps the input data in a "wrapper"
dictionary with one key, "someKey", with the input data as its value.
The flag `--unwrap someKey` does the opposite: if it is specified only
the value stored under the key "someKey" in the top-level dictionary
element of the input data is converted to the target format and output; all
other data is ignored.  If the top-level element is not a dictionary or does not
have the key "someKey" then `--unwrap someKey` returns an error.

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

MIT.  See the file `LICENSE`.

`example.toml` from <https://github.com/toml-lang/toml>.  `example.json`,
`example.msgpack`, `example.cbor`, `example.yml`, `tests/bin.msgpack`,
and `tests/bin.yml` are derived from it.
