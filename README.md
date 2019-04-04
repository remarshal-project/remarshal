# remarshal

[![Travis CI Build Status](https://travis-ci.org/dbohdan/remarshal.svg?branch=master)](https://travis-ci.org/dbohdan/remarshal)
[![AppVeyor CI Build Status](https://ci.appveyor.com/api/projects/status/github/dbohdan/remarshal?branch=master&svg=true)](https://ci.appveyor.com/project/dbohdan/remarshal)

Convert between TOML, YAML and JSON. When installed provides the command line
commands `toml2yaml`, `toml2json`, `yaml2toml`, `yaml2json`. `json2toml` and
`json2yaml` for format conversion as well as `toml2toml`, `yaml2yaml` and
`json2json` for reformatting and error detection.

# Installation

You will need Python 2.7 or Python 3.5 or later. Earlier versions of Python 3
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

# Usage

```
usage: remarshal.py [-h] [-i INPUT] [-o OUTPUT] -if {json,toml,yaml} -of
                    {json,toml,yaml} [--indent-json] [--yaml-style {,',",|,>}]
                    [--wrap WRAP] [--unwrap UNWRAP] [--preserve-key-order]
                    [-v]
                    [inputfile]
```

```
usage: {json,toml,yaml}2toml [-h] [-i INPUT] [-o OUTPUT]
       [--wrap WRAP] [--unwrap UNWRAP]
       [--preserve-key-order] [-v]
       [inputfile]
```

```
usage: {json,toml,yaml}2yaml [-h] [-i INPUT] [-o OUTPUT]
       [--yaml-style {,',",|,>}] [--wrap WRAP] [--unwrap UNWRAP]
       [--preserve-key-order] [-v]
       [inputfile]
```

```
usage: {json,toml,yaml}2json [-h] [-i INPUT] [-o OUTPUT]
       [--indent-json] [--wrap WRAP] [--unwrap UNWRAP]
       [--preserve-key-order] [-v]
       [inputfile]
```

All of the commands above exit with status 0 on success, 1 on operational
failure and 2 when they fail to parse the command line.

If no `inputfile` or `-i INPUT` is given or it is `-` or a blank string the data
to convert is read from standard input. If no `-o OUTPUT` is given or it is `-`
or a blank string the result of the conversion is written to standard output.

For the short commands (`x2y`) the flag `-i` before `inputfile` can be omitted
if `inputfile` is the last argument.

## Wrappers

The flags `--wrap` and `--unwrap` are there to solve the problem of converting
JSON and YAML data to TOML if the topmost element of that data is not of a
dictionary type (i.e., not an object in JSON or an associative array in YAML)
but a list, a string or a number. Such data can not be represented as TOML
directly; it needs to wrapped in a dictionary first. Passing the flag
`--wrap someKey` to `remarshal` or one of its short commands wraps the input
data in a "wrapper" dictionary with one key, "someKey", with the input data as
its value. The flag `--unwrap someKey` does the opposite: if it is specified
only the value stored under the key "someKey" in the top-level dictionary
element of the input data is converted to the target format and output; all
other data is skipped. If the top-level element is not a dictionary or does not
have the key `someKey` then `--unwrap someKey` returns an error.

The following shell transcript demonstrates the problem and how `--wrap` and
`--unwrap` solve it:

```
$ echo '[{"a":"b"},{"c":[1,2,3]}]' | ./remarshal.py -if json -of toml
Error: cannot convert non-dictionary data to TOML; use "wrap" to wrap it in a dictionary

$ echo '[{"a":"b"},{"c":[1,2,3]}]' | \
./remarshal.py -if json -of toml --wrap main
[[main]]
a = "b"

[[main]]
c = [1, 2, 3]

$ echo '[{"a":"b"},{"c":[1,2,3]}]' | \
./remarshal.py -if json -of toml --wrap main > test.toml

$ ./remarshal.py -if toml -of json < test.toml
{"main":[{"a":"b"},{"c":[1,2,3]}]}

$ ./remarshal.py -if toml -of json --unwrap main < test.toml
[{"a":"b"},{"c":[1,2,3]}]
```

# Examples

```
$ ./remarshal.py -i example.toml -if toml -of yaml
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

$ curl -s http://api.openweathermap.org/data/2.5/weather\?q\=Kiev,ua | \
./remarshal.py -if json -of toml
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

# License

MIT. See the file `LICENSE`.

`example.toml` from <https://github.com/toml-lang/toml>. `example.yaml` and
`example.json` are derived from it.
