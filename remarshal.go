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

const (
	defaultFormatFlagValue = "unspecified"
	defaultWrapFlagValue = "key"
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
// This approach is meant to prevent encoders from putting numbers stored as
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
	case defaultFormatFlagValue:
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

// unmarshal decodes serialized data in the format inputFormat into a structure
// of nested maps and slices.
func unmarshal(input []byte, inputFormat format) (data interface{},
	err error) {
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
	return
}

// marshal encodes data stored in nested maps and slices in the format
// outputFormat.
func marshal(data interface{}, outputFormat format,
	indentJSON bool) (result []byte, err error) {
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

// processCommandLine parses the command line arguments (including os.Args[0],
// the program name) and sets the input and the output file names as well as
// other conversion options based on them.
func processCommandLine() (inputFile string, outputFile string,
	inputFormat format, outputFormat format,
	indentJSON bool, wrap string, unwrap string) {
	var inputFormatStr, outputFormatStr string

	flag.StringVar(&inputFile, "i", "-", "input file")
	flag.StringVar(&outputFile, "o", "-", "output file")
	flag.StringVar(&wrap, "wrap", defaultWrapFlagValue,
		"wrap the data in a map type with the given key")
	flag.StringVar(&unwrap, "unwrap", defaultWrapFlagValue,
		"only output the data stored under the given key")

	// See if our program is named, e.g., "json2yaml" (normally due to having
	// been started through a symlink).
	inputFormat, outputFormat, err := filenameToFormat(os.Args[0])
	formatFromProgramName := err == nil
	if !formatFromProgramName {
		// Only give the user an option to specify the input and the output
		// format with flags when it is mandatory, i.e., when we are *not* being
		// run as "json2yaml" or similar. This makes the usage messages for the
		// "x2y" commands more accurate as well.
		flag.StringVar(&inputFormatStr, "if", defaultFormatFlagValue,
			"input format ('toml', 'yaml' or 'json')")
		flag.StringVar(&outputFormatStr, "of", defaultFormatFlagValue,
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
	return
}

func main() {
	inputFile, outputFile, inputFormat, outputFormat,
	indentJSON, wrap, unwrap := processCommandLine()

	// Read the input data from either standard input or a file.
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
	if err != nil {
		fmt.Println(err)
		os.Exit(1)

	}

	// Convert the input data from inputFormat to outputFormat.
	data, err := unmarshal(input, inputFormat)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	// Unwrap and/or wrap the data in a map if we were told to.
	if unwrap != defaultWrapFlagValue {
		temp, ok := data.(map[string]interface{})
		if !ok {
			fmt.Printf("cannot unwrap data: top-level value not a map\n")
			os.Exit(1)
		}
		data, ok = temp[unwrap]
		if !ok {
			fmt.Printf("cannot unwrap data: no key '%s'\n", unwrap)
			os.Exit(1)
		}
	}
	if wrap != defaultWrapFlagValue {
		data = map[string]interface{}{wrap: data}
	}
	output, err := marshal(data, outputFormat, indentJSON)
	if err != nil {
		fmt.Printf("cannot convert data: %v\n", err)
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
