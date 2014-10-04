// yaml2toml
// Copyright (C) 2014, Danyil Bohdan
// License: MIT
package main

import (
	"bytes"
	"flag"
	"fmt"
	"github.com/BurntSushi/toml"
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"os"
)

// Recursively convert map[interface{}]interface{} to map[string]interface{}.
// This is needed for the TOML encoder to accept our data, which is returned as
// an interface{} map by the YAML decoder.
func convertToStringMap(m map[interface{}]interface{}) (
	res map[string]interface{}, err error) {
	res = make(map[string]interface{})
	for k, v := range m {
		switch v.(type) {
		case map[interface{}]interface{}:
			var err error
			res[k.(string)], err =
				convertToStringMap(v.(map[interface{}]interface{}))
			if err != nil {
				return nil, err
			}
		default:
			res[k.(string)] = v
		}
	}
	return
}

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

	if err := yaml.Unmarshal(input, &data); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	switch data.(type) {
	case map[string]interface{}:
		{
			// for encoding/json
		}
	default:
		// for gopkg.in/yaml.v2
		data, err = convertToStringMap(data.(map[interface{}]interface{}))
		if err != nil {
			fmt.Println(err)
			os.Exit(1)
		}
	}

	buf := new(bytes.Buffer)
	if err := toml.NewEncoder(buf).Encode(data); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	// Print result to stdout or file.
	if outputFile == "" || outputFile == "-" {
		fmt.Printf("%s\n", buf.String())
	} else {
		err := ioutil.WriteFile(outputFile, buf.Bytes(), 0644)
		if err != nil {
			fmt.Printf("can't write to file '%s'\n", outputFile)
			os.Exit(1)
		}
	}
}
