#!/bin/sh
set -e

cp example.toml /tmp/toml
cp example.yaml /tmp/yaml
cp example.json /tmp/json

for if in toml yaml json; do
	for of in toml yaml json; do
		echo "--- $if -> $of"
		./remarshal -i "/tmp/$if" -o "/tmp/$of.2" -if $if -of $of
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
