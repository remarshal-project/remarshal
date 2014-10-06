// remarshal, a utility to convert between serialization formats.
// Copyright (C) 2014 Danyil Bohdan
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

// convertMapsToStringMaps recursively converts values of type
// map[interface{}]interface{} contained in item to map[string]interface{}. This
// is needed before the encoders for TOML and JSON can accept data returned by
// the YAML decoder.
func convertMapsToStringMaps(item interface{}) (res interface{}, err error) {
	switch item.(type) {
	case map[interface{}]interface{}:
		res := make(map[string]interface{})
		for k, v := range item.(map[interface{}]interface{}) {
			res[k.(string)], err = convertMapsToStringMaps(v)
			if err != nil {
				return nil, err
			}
		}
		return res, nil
	case []interface{}:
		res := make([]interface{}, len(item.([]interface{})))
		for i, v := range item.([]interface{}) {
			res[i], err = convertMapsToStringMaps(v)
			if err != nil {
				return nil, err
			}
		}
		return res, nil
	default:
		return item, nil
	}
}

// convertNumberToInt64 recursively walks the structures contained in item
// converting values of the type json.Number to int64 or, failing that, float64.
// This approach is meant to prevent encoders putting numbers stored as
// json.Number in quotes or encoding large intergers in scientific notation.
func convertNumberToInt64(item interface{}) (res interface{}, err error) {
	switch item.(type) {
	case map[string]interface{}:
		res := make(map[string]interface{})
		for k, v := range item.(map[string]interface{}) {
			res[k], err = convertNumberToInt64(v)
			if err != nil {
				return nil, err
			}
		}
		return res, nil
	case []interface{}:
		res := make([]interface{}, len(item.([]interface{})))
		for i, v := range item.([]interface{}) {
			res[i], err = convertNumberToInt64(v)
			if err != nil {
				return nil, err
			}
		}
		return res, nil
	case json.Number:
		n, err := item.(json.Number).Int64()
		if err != nil {
			f, err := item.(json.Number).Float64()
			if err != nil {
				// Can't convert to Int64.
				return item, nil
			}
			return f, nil
		}
		return n, nil
	default:
		return item, nil
	}
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
			data, err = convertMapsToStringMaps(data)
		}
	case fJSON:
		decoder := json.NewDecoder(bytes.NewReader(input))
		decoder.UseNumber()
		err = decoder.Decode(&data)
		if err == nil {
			data, err = convertNumberToInt64(data)
		}
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
	formatFromProgramName := err == nil
	if !formatFromProgramName {
		// Only give the user an option to specify the input and the output
		// format with flags when it is mandatory, i.e., when we are *not* being
		// run as "json2yaml" or similar. This makes the usage messages for the
		// "x2y" commands more accurate as well.
		flag.StringVar(&inputFormatStr, "if", "unknown",
			"input format ('toml', 'yaml' or 'json')")
		flag.StringVar(&outputFormatStr, "of", "unknown",
			"input format ('toml', 'yaml' or 'json')")
	}
	if !formatFromProgramName || outputFormat == fJSON {
		flag.BoolVar(&indentJSON, "indent-json", true, "indent JSON output")
	}
	flag.Parse()
	if !formatFromProgramName {
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

	// Check for extraneous command line arguments. If we are running as "x2y"
	// set inputFile if given on the command line without the -i flag.
	tail := flag.Args()
	if len(tail) > 0 {
		if formatFromProgramName && len(tail) == 1 &&
			(inputFile == "" || inputFile == "-") {
			inputFile = flag.Arg(0)
		} else {
			if len(tail) == 1 {
				fmt.Print("extraneous command line argument:")
			} else {
				fmt.Print("extraneous command line arguments:")
			}
			for _, a := range tail {
				fmt.Printf(" '%s'", a)
			}
			fmt.Printf("\n")
			os.Exit(1)
		}
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
		err = ioutil.WriteFile(outputFile, output, 0644)
		if err != nil {
			fmt.Printf("cannot write to file %s\n", outputFile)
			os.Exit(1)
		}
	}
}
