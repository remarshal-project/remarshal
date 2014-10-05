// remarshal, a utility to convert between serialization formats.
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

type format int

const (
	fTOML format = iota
	fYAML
	fJSON
	fPlaceholder
	fUnknown
)

// convertToStringMap recursively converts map[interface{}]interface{} to
// map[string]interface{}. This is needed for the TOML and JSON encoders to
// accept the data returned by the YAML decoder.
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

func stringToFormat(s string) (f format, err error) {
	switch s {
	case "toml":
		return fTOML, nil
	case "yaml":
		return fYAML, nil
	case "json":
		return fJSON, nil
	case "unknown":
		return fPlaceholder, errors.New("placeholder format")
	default:
		return fUnknown, errors.New("cannot convert string to format: '" +
			s + "'")
	}
}

// filenameToFormat tries to parse string s as "<formatName>2<formatName>".
// Return both formats as type format if successful.
func filenameToFormat(s string) (inputf format, outputf format, err error) {
	filenameParts := strings.Split(filepath.Base(s), "2")
	if len(filenameParts) != 2 {
		return fUnknown, fUnknown, errors.New(
			"cannot determine format from filename")
	}
	prefix, err := stringToFormat(filenameParts[0])
	if err != nil {
		return fUnknown, fUnknown, err
	}
	suffix, err := stringToFormat(filenameParts[1])
	if err != nil {
		return fUnknown, fUnknown, err
	}
	return prefix, suffix, nil
}

func main() {
	var data interface{}
	var inputFile, outputFile, inputFormatStr, outputFormatStr string
	var inputFormat, outputFormat format

	// Parse command line arguments and choose the input and output formats.
	flag.StringVar(&inputFile, "i", "-", "input file")
	flag.StringVar(&outputFile, "o", "-", "output file")
	var ferr error
	// See if our executable is named, e.g., "json2yaml".
	inputFormat, outputFormat, ferr = filenameToFormat(os.Args[0])
	formatFromArgsZero := ferr == nil
	if !formatFromArgsZero {
		flag.StringVar(&inputFormatStr, "if", "unknown",
			"input format ('toml', 'yaml' or 'json')")
		flag.StringVar(&outputFormatStr, "of", "unknown",
			"input format ('toml', 'yaml' or 'json')")
	}
	flag.Parse()
	if !formatFromArgsZero {
		if inputFormat, ferr = stringToFormat(inputFormatStr); ferr != nil {
			fmt.Printf("")
			if inputFormat == fPlaceholder {
				fmt.Println("please specify the input format")
			} else {
				fmt.Printf("please specify a valid input format (given '%s')\n",
					inputFormatStr)
			}
			os.Exit(1)
		}
		if outputFormat, ferr = stringToFormat(outputFormatStr); ferr != nil {
			if outputFormat == fPlaceholder {
				fmt.Println("please specify the output format")
			} else {
				fmt.Printf(
					"please specify a valid output format (given '%s')\n",
					outputFormatStr)
			}
			os.Exit(1)
		}
	}

	// Check for extraneous arguments.
	tail := flag.Args()
	if len(tail) > 0 {
		if len(tail) == 1 {
			fmt.Print("unknown command line argument: ")
		} else {
			fmt.Print("unknown command line arguments: ")
		}
		for _, a := range tail {
			fmt.Printf("%s ", a)
		}
		fmt.Printf("\n")
		os.Exit(1)
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
	case fTOML:
		_, decerr = toml.Decode(string(input), &data)
	case fYAML:
		decerr = yaml.Unmarshal(input, &data)
		if decerr == nil {
			data, decerr = convertToStringMap(
				data.(map[interface{}]interface{}))
		}
	case fJSON:
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
	case fTOML:
		{
			buf := new(bytes.Buffer)
			encerr = toml.NewEncoder(buf).Encode(data)
			result = buf.Bytes()
		}
	case fYAML:
		result, encerr = yaml.Marshal(&data)
	case fJSON:
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
			fmt.Printf("cannot write to file %s\n", outputFile)
			os.Exit(1)
		}
	}
}
