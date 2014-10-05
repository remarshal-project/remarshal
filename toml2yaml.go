// toml2yaml
// Copyright (C) 2014, Danyil Bohdan
// License: MIT
package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"github.com/BurntSushi/toml"
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"
)

type Format int

const (
	ftoml Format = iota
	fyaml
	fjson
	funknown
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

func stringToFormat(s string) (f Format, err error) {
	switch s {
	case "toml":
		return ftoml, nil
	case "yaml":
		return fyaml, nil
	case "json":
		return fjson, nil
	default:
		return funknown, errors.New("cannot convert string to Format: '" +
			s + "'")
	}
}

func filenameToFormat(s string) (inputf Format, outputf Format, err error) {
	filenameParts := strings.Split(filepath.Base(s), "2")
	if len(filenameParts) != 2 {
		return funknown, funknown, errors.New("cannot determine Format from filename")
	}
	prefix, err := stringToFormat(filenameParts[0])
	if err != nil {
		return funknown, funknown, err
	}
	suffix, err := stringToFormat(filenameParts[1])
	if err != nil {
		return funknown, funknown, err
	}
	return prefix, suffix, nil
}

func main() {
	var data interface{}
	var inputFile, outputFile, inputFormatStr, outputFormatStr string
	var inputFormat, outputFormat Format

	flag.StringVar(&inputFile, "i", "-", "input file")
	flag.StringVar(&outputFile, "o", "-", "output file")
	flag.StringVar(&inputFormatStr, "if", "toml",
		"input format ('toml', 'yaml' or 'json')")
	flag.StringVar(&outputFormatStr, "of", "yaml",
		"input format ('toml', 'yaml' or 'json')")
	flag.Parse()

	var ferr error
	// See if our executable is named, e.g., "json2yaml".
	inputFormat, outputFormat, ferr = filenameToFormat(os.Args[0])
	if ferr != nil {
		if inputFormat, ferr = stringToFormat(inputFormatStr); ferr != nil {
			fmt.Println(ferr)
			os.Exit(1)
		}
		if outputFormat, ferr = stringToFormat(outputFormatStr); ferr != nil {
			fmt.Println(ferr)
			os.Exit(1)
		}
	}

	// Read the input data from either stdin or a file.
	var input []byte
	var ierr error
	if inputFile == "" || inputFile == "-" {
		input, ierr = ioutil.ReadAll(os.Stdin)
	} else {
		if _, ierr := os.Stat(inputFile); os.IsNotExist(ierr) {
			fmt.Printf("no such file or directory: '%s'\n", inputFile)
			os.Exit(1)
		}
		input, ierr = ioutil.ReadFile(inputFile)
	}
	if ierr != nil {
		fmt.Println(ierr)
		os.Exit(1)

	}

	// Decode the serialized data.
	var decerr error
	switch inputFormat {
	case ftoml:
		_, decerr = toml.Decode(string(input), &data)
	case fyaml:
		decerr = yaml.Unmarshal(input, &data)
		if decerr == nil {
			data, decerr = convertToStringMap(data.(map[interface{}]interface{}))
		}
	case fjson:
		decerr = json.Unmarshal(input, &data)
	}
	if decerr != nil {
		fmt.Println(decerr)
		os.Exit(1)
	}

	// Reencode the data in the output format.
	var result []byte
	var encerr error
	switch outputFormat {
	case ftoml:
		{
			buf := new(bytes.Buffer)
			encerr = toml.NewEncoder(buf).Encode(data)
			result = buf.Bytes()
		}
	case fyaml:
		result, encerr = yaml.Marshal(&data)
	case fjson:
		result, encerr = json.Marshal(&data)
	}
	if encerr != nil {
		fmt.Println(encerr)
		os.Exit(1)

	}

	// Print the result to stdout or file.
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
