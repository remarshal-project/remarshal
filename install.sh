#!/bin/sh
targetDir=/usr/local/bin
cp remarshal $targetDir
for if in toml yaml json; do
	for of in toml yaml json; do
		ln -s "$targetDir/remarshal" "$targetDir/${if}2${of}"
	done
done
