Convert between TOML, YAML and JSON. When installed provides the command line
commands `toml2yaml`, `toml2json`, `yaml2toml`, `yaml2json`. `json2toml` and
`json2yaml` for format conversion as well as `toml2toml`, `yaml2yaml` and
`json2json` for reformatting and error detection.

# Usage

```
remarshal [-i inputfile] [-o outputfile] -if inputformat -of outputformat
          [-indent-json=(true|false)]
```

where `inputformat` and `outputformat` can each be one of `toml`, `yaml` and
`json` or

```
toml2yaml [-i inputfile] [-o outputfile]
toml2json [-i inputfile] [-o outputfile] [-indent-json=(true|false)]
yaml2toml [-i inputfile] [-o outputfile]
yaml2json [-i inputfile] [-o outputfile] [-indent-json=(true|false)]
json2toml [-i inputfile] [-o outputfile]
json2yaml [-i inputfile] [-o outputfile]
toml2toml [-i inputfile] [-o outputfile]
yaml2yaml [-i inputfile] [-o outputfile]
json2json [-i inputfile] [-o outputfile] [-indent-json=(true|false)]
```

The all of the above commands exit with status 0 on success and 1 on failure.

If `inputfile` is not given or is `-` or a blank string the data to convert is
read from standard input. If `outputfile` is not given or is `-` or a blank
string the result of the conversion is written to standard output.

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
