#!/bin/sh
build() {
    echo "Building $1"
    go build $1
}

set -e
build toml2yaml.go

echo "Yuck! Using sed(1) to generate the code for toml2json.go..."
sed -e 's|yaml.Marshal|json.Marshal|;s|gopkg.in/yaml.v2|encoding/json|' < toml2yaml.go > toml2json.go
build toml2json.go
rm toml2json.go

build yaml2toml.go

echo "Generating code again, now for json2toml.go"
sed -e 's|yaml.Unmarshal|json.Unmarshal|;s|gopkg.in/yaml.v2|encoding/json|' < yaml2toml.go > json2toml.go
build json2toml.go
rm json2toml.go

echo Success
