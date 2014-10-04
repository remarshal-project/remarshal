// toml2yaml
// Copyright (C) 2014, Danyil Bohdan
// License: MIT
package main

import (
	"flag"
	"fmt"
	"github.com/BurntSushi/toml"
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"os"
)

func main() {
	var data interface{}
	var inputFile, outputFile string
	flag.StringVar(&inputFile, "i", "-", "input file")
	flag.StringVar(&outputFile, "o", "-", "output file")
	flag.Parse()

	// Read the input data from either stdin or a file.
	var input []byte
	var err error
	if inputFile == "" || inputFile == "-" {
		input, err = ioutil.ReadAll(os.Stdin)
	} else {
		if _, err := os.Stat(inputFile); os.IsNotExist(err) {
			fmt.Printf("no such file or directory: '%s'\n", inputFile)
			os.Exit(1)
		}
		input, err = ioutil.ReadFile(inputFile)
	}

	// Decode the TOML and reencode it as YAML.
	if _, err := toml.Decode(string(input), &data); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	result, err := yaml.Marshal(&data)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)

	}

	// Print result to stdout or file.
	if outputFile == "" || outputFile == "-" {
		fmt.Printf("%s\n", string(result))
	} else {
		err := ioutil.WriteFile(outputFile, result, 0644)
		if err != nil {
			fmt.Printf("can't write to file '%s'\n", outputFile)
			os.Exit(1)
		}
	}
}
