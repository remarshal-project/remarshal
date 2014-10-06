# remarshal

Convert between TOML, YAML and JSON. When installed provides the command line
commands `toml2yaml`, `toml2json`, `yaml2toml`, `yaml2json`. `json2toml` and
`json2yaml` for format conversion as well as `toml2toml`, `yaml2yaml` and
`json2json` for reformatting and error detection.

# Usage

```
remarshal -if inputformat -of outputformat [-indent-json=(true|false)]
          [-i inputfile] [-o outputfile] [-wrap wrapper] [-unwrap wrapper]

```

where `inputformat` and `outputformat` can each be `toml`, `yaml` or
`json`.

```
toml2toml [-wrap wrapper] [-unwrap wrapper] [-o outputfile] [[-i] inputfile]
yaml2toml [-wrap wrapper] [-unwrap wrapper] [-o outputfile] [[-i] inputfile]
json2toml [-wrap wrapper] [-unwrap wrapper] [-o outputfile] [[-i] inputfile]
toml2yaml [-wrap wrapper] [-unwrap wrapper] [-o outputfile] [[-i] inputfile]
yaml2yaml [-wrap wrapper] [-unwrap wrapper] [-o outputfile] [[-i] inputfile]
json2yaml [-wrap wrapper] [-unwrap wrapper] [-o outputfile] [[-i] inputfile]
toml2json [-indent-json=(true|false)] [-wrap wrapper] [-unwrap wrapper]
          [-o outputfile] [[-i] inputfile]
yaml2json [-indent-json=(true|false)] [-wrap wrapper] [-unwrap wrapper]
          [-o outputfile] [[-i] inputfile]
json2json [-indent-json=(true|false)] [-wrap wrapper] [-unwrap wrapper]
          [-o outputfile] [[-i] inputfile]
```

All of the commands above exit with status 0 on success and 1 on failure.

If no `inputfile` is given or it is `-` or a blank string the data to convert is
read from standard input. If no `outputfile` is given or it is `-` or a blank
string the result of the conversion is written to standard output.

For the short commands (`x2y`) the flag `-i` before `inputfile` can be omitted
if `inputfile` is the last argument.

## Wrappers

The flags `-wrap` and `-unwrap` are there to solve the problem of converting
JSON and YAML data to TOML if the topmost element of that data is not of a map
type (i.e., not an object in JSON or an associative array in YAML) but a list, a
string or a number. Such data can not be represented as TOML directly; it needs
to wrapped in a map type first. Passing the flag `-wrap someKey` to `remarshal`
or one of its short commands wraps the input data in a "wrapper" map with one
key, "someKey", with the input data as its value. The flag `-unwrap someKey`
does the opposite: if it is specified only the value stored under the key
"someKey" in the top-level map element of the input data is converted to the
target format and output; all other data is skipped. If the top-level element is
not a map or does not have the key `someKey` then `-unwrap someKey` returns an
error.

The following shell transcript demonstrates the problem and how `-wrap` and
`-unwrap` solve it:

```
$ echo '[{"a":"b"},{"c":[1,2,3]}]' | ./remarshal -if json -of toml
cannot convert data: top-level values must be a Go map or struct

$ echo '[{"a":"b"},{"c":[1,2,3]}]' | \
./remarshal -if json -of toml -wrap main
[[main]]
  a = "b"

[[main]]
  c = [1, 2, 3]

$ echo '[{"a":"b"},{"c":[1,2,3]}]' | \
./remarshal -if json -of toml -wrap main > test.toml

$ ./remarshal -if toml -of json -indent-json=0 < test.toml
{"main":[{"a":"b"},{"c":[1,2,3]}]}

$ ./remarshal -if toml -of json -indent-json=0 -unwrap main < test.toml
[{"a":"b"},{"c":[1,2,3]}]
```

# Building and installation

Tested with `go version go1.2.2 linux/amd64`. Do the following to install
`remarshal`:

```sh
go get github.com/BurntSushi/toml
go get gopkg.in/yaml.v2
git clone https://github.com/dbohdan/remarshal.git
cd remarshal
go build remarshal.go
sh tests.sh
sudo sh install.sh # install into /usr/local/bin
```

# Examples

```
$ ./remarshal -i example.toml -if toml -of yaml
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
  bio: |-
    GitHub Cofounder & CEO
    Likes tater tots and beer.
  dob: 1979-05-27T07:32:00Z
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
./remarshal -if json -of toml
base = "cmc stations"
cod = 200
dt = 1412532000
id = 703448
name = "Kiev"

[clouds]
  all = 44

[coord]
  lat = 50.43
  lon = 30.52

[main]
  humidity = 66
  pressure = 1026
  temp = 283.49
  temp_max = 284.15
  temp_min = 283.15

[sys]
  country = "UA"
  id = 7358
  message = 0.2437
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

# Known bugs

* Converting data with floating point values to YAML may cause a loss of
precision.

# License

MIT. See the file `LICENSE`.

`example.toml` from <https://github.com/toml-lang/toml>.
