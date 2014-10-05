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
// map[string]interface{}. This is needed before the TOML and JSON encoders can
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
	switch strings.ToLower(s) {
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
// It returns both formats as type format if successful.
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

// remarshal converts input data of format inputFormat to outputFormat and
// returns the result.
func remarshal(input []byte, inputFormat format, outputFormat format,
	indentJSON bool) (result []byte, err error) {
	var data interface{}

	// Decode the serialized data.
	switch inputFormat {
	case fTOML:
		_, err = toml.Decode(string(input), &data)
	case fYAML:
		err = yaml.Unmarshal(input, &data)
		if err == nil {
			data, err = convertToStringMap(
				data.(map[interface{}]interface{}))
		}
	case fJSON:
		err = json.Unmarshal(input, &data)
	}
	if err != nil {
		return nil, err
	}

	// Reencode the data in the output format.
	switch outputFormat {
	case fTOML:
		buf := new(bytes.Buffer)
		err = toml.NewEncoder(buf).Encode(data)
		result = buf.Bytes()
	case fYAML:
		result, err = yaml.Marshal(&data)
	case fJSON:
		result, err = json.Marshal(&data)
		if err == nil && indentJSON {
			buf := new(bytes.Buffer)
			err = json.Indent(buf, result, "", "  ")
			result = buf.Bytes()
		}
	}
	if err != nil {
		return nil, err
	}

	return
}

func main() {
	var inputFile, outputFile, inputFormatStr, outputFormatStr string
	var inputFormat, outputFormat format
	indentJSON := true

	// Parse the command line arguments and choose the input and the output
	// format.
	flag.StringVar(&inputFile, "i", "-", "input file")
	flag.StringVar(&outputFile, "o", "-", "output file")

	// See if our executable is named, e.g., "json2yaml".
	inputFormat, outputFormat, err := filenameToFormat(os.Args[0])
	formatFromArgsZero := err == nil
	if !formatFromArgsZero {
		// Only give the user an option to specify the input and the output
		// format with flags when it is mandatory, i.e., when we are *not* being
		// run as "json2yaml" or similar. This makes the usage messages for the
		// "x2y" commands more accurate as well.
		flag.StringVar(&inputFormatStr, "if", "unknown",
			"input format ('toml', 'yaml' or 'json')")
		flag.StringVar(&outputFormatStr, "of", "unknown",
			"input format ('toml', 'yaml' or 'json')")
	}
	if !formatFromArgsZero || outputFormat == fJSON {
		flag.BoolVar(&indentJSON, "indent-json", true, "indent JSON output")
	}
	flag.Parse()
	if !formatFromArgsZero {
		// Try to parse the format options we were given through the command
		// line flags.
		if inputFormat, err = stringToFormat(inputFormatStr); err != nil {
			if inputFormat == fPlaceholder {
				fmt.Println("please specify the input format")
			} else {
				fmt.Printf("please specify a valid input format ('%s' given)\n",
					inputFormatStr)
			}
			os.Exit(1)
		}
		if outputFormat, err = stringToFormat(outputFormatStr); err != nil {
			if outputFormat == fPlaceholder {
				fmt.Println("please specify the output format")
			} else {
				fmt.Printf(
					"please specify a valid output format ('%s' given)\n",
					outputFormatStr)
			}
			os.Exit(1)
		}
	}

	// Check for extraneous command line arguments.
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

	// Read the input data from either standard input or a file.
	var input []byte
	if inputFile == "" || inputFile == "-" {
		input, err = ioutil.ReadAll(os.Stdin)
	} else {
		if _, err := os.Stat(inputFile); os.IsNotExist(err) {
			fmt.Printf("no such file or directory: '%s'\n", inputFile)
			os.Exit(1)
		}
		input, err = ioutil.ReadFile(inputFile)
	}
	if err != nil {
		fmt.Println(err)
		os.Exit(1)

	}

	output, err := remarshal(input, inputFormat, outputFormat, indentJSON)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}

	// Print the result to either standard output or a file.
	if outputFile == "" || outputFile == "-" {
		fmt.Printf("%s\n", string(output))
	} else {
		err := ioutil.WriteFile(outputFile, output, 0644)
		if err != nil {
			fmt.Printf("cannot write to file %s\n", outputFile)
			os.Exit(1)
		}
	}
}
