#!/bin/sh
set -e

cp example.toml /tmp/toml
./toml2yaml -i example.toml -if toml -of json -o /tmp/json
./toml2yaml -i example.toml -if toml -of yaml -o /tmp/yaml

for if in toml yaml json; do
	for of in toml yaml json; do
		echo "--- $if -> $of"
		./toml2yaml -i "/tmp/$if" -o "/tmp/$of.2" -if $if -of $of
		if test "$1" = "-v"; then
			cat "/tmp/$of.2"
		fi
		if test "$of" != "toml"; then
			diff "/tmp/$of" "/tmp/$of.2"
		fi
	done
done

for filename in toml yaml json; do
	rm "/tmp/$filename" "/tmp/$filename.2"
done
