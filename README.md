Provides command line utilities `toml2yaml`, `toml2json`, `yaml2toml`,
`json2toml`.

# Usage

```
toml2yaml [-i inputfile] [-o outputfile]
toml2json [-i inputfile] [-o outputfile]
yaml2toml [-i inputfile] [-o outputfile]
json2toml [-i inputfile] [-o outputfile]
```

# Building

Tested with `go version go1.2.2 linux/amd64`. Do the following:

```
go get github.com/BurntSushi/toml
go get gopkg.in/yaml.v2
git clone https://github.com/dbohdan/toml2yaml.git
cd toml2yaml
sh compile.sh
sudo cp toml2yaml toml2json yaml2toml json2toml /usr/local/bin/
```

# Example

```
$ ./toml2yaml -i example.toml
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

MIT. See file `LICENSE`.
