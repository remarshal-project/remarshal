Convert between TOML, YAML and JSON. When installed provides the command line
commands `toml2yaml`, `toml2json`, `yaml2toml`, `yaml2json`. `json2toml` and
`json2yaml` for format conversion as well as `toml2toml`, `yaml2yaml` and
`json2json` for reformatting and error detection.

# Usage

```
remarshal -if inputformat -of outputformat [-indent-json=(true|false)]
          [-i inputfile] [-o outputfile]

```

where `inputformat` and `outputformat` can each be one of `toml`, `yaml` and
`json`.

```
toml2yaml [-o outputfile] [[-i] inputfile]
toml2json [-indent-json=(true|false)] [-o outputfile] [[-i] inputfile]
yaml2toml [-o outputfile] [[-i] inputfile]
yaml2json [-indent-json=(true|false)] [-o outputfile] [[-i] inputfile]
json2toml [-o outputfile] [[-i] inputfile]
json2yaml [-o outputfile] [[-i] inputfile]
toml2toml [-o outputfile] [[-i] inputfile]
yaml2yaml [-o outputfile] [[-i] inputfile]
json2json [-indent-json=(true|false)] [-o outputfile] [[-i] inputfile]
```

The all of the above commands exit with status 0 on success and 1 on failure.

If `inputfile` is not given or is `-` or a blank string the data to convert is
read from standard input. If `outputfile` is not given or is `-` or a blank
string the result of the conversion is written to standard output.

For short commands (`x2y`) the flag `-i` before `inputfile` can be omitted if
`inputfile` is the last argument.

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

# Example

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
servers:
  alpha:
    dc: eqdc10
    ip: 10.0.0.1
  beta:
    dc: eqdc10
    ip: 10.0.0.2
title: TOML Example
```

# License

MIT. See the file `LICENSE`.
