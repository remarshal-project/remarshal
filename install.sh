#!/bin/sh
targetDir=/usr/local/bin
cp toml2yaml $targetDir
for if in toml yaml json; do
	for of in toml yaml json; do
		ln -s "$targetDir/toml2yaml" "$targetDir/${if}2${of}"
	done
done
