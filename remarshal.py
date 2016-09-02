#! /usr/bin/env python
# remarshal, a utility to convert between serialization formats.
# Copyright (C) 2014, 2015, 2016 dbohdan
# License: MIT

from __future__ import print_function

import argparse
import datetime
import dateutil.parser
import io
import json
import os.path
import re
import string
import sys
import pytoml
import yaml

FORMATS = ['json', 'toml', 'yaml']
__version__ = '0.4.0'

def filename2format(filename):
    try:
        from_, to = filename.split('2', 1)
    except ValueError:
        return False, None, None
    if from_ in FORMATS and to in FORMATS:
        return True, from_, to
    else:
        return False, None, None


def json_serialize(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("{0} is not JSON serializable".format(repr(obj)))


# Fix loss of time zone inforation.
# http://stackoverflow.com/questions/13294186/can-pyyaml-parse-iso8601-dates
def timestamp_constructor(loader, node):
    return dateutil.parser.parse(node.value)
yaml.add_constructor(u'tag:yaml.org,2002:timestamp', timestamp_constructor)


def parse_command_line(argv):
    me = os.path.basename(argv[0])
    format_from_filename, from_, to = filename2format(me)

    parser = argparse.ArgumentParser(description='Convert between JSON, TOML ' +
                                    'and YAML.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--input', dest='input_flag', metavar='INPUT',
                        default=None, help='input file')
    group.add_argument('inputfile', nargs='?', default='-', help='input file')

    parser.add_argument('-o', '--output', dest='output', default='-',
                        help='output file')
    if not format_from_filename:
        parser.add_argument('-if', '--input-format', dest='input_format',
                            required=True, help="input format", choices=FORMATS)
        parser.add_argument('-of', '--output-format', dest='output_format',
                            required=True, help="output format",
                            choices=FORMATS)
    if not format_from_filename or to == 'json':
        parser.add_argument('--indent-json', dest='indent_json',
                            action='store_const', const=2, default=None,
                            help='indent JSON output')
    parser.add_argument('--wrap', dest='wrap', default=None,
                        help='wrap the data in a map type with the given key')
    parser.add_argument('--unwrap', dest='unwrap', default=None,
                        help='only output the data stored under the given key')

    args = parser.parse_args(args=argv[1:])

    if args.input_flag is not None:
        args.input = args.input_flag
    else:
        args.input = args.inputfile
    if format_from_filename:
        args.input_format = from_
        args.output_format = to
        if to != 'json':
            args.__dict__['indent_json'] = None

    return args


def run(argv):
    args = parse_command_line(argv)
    remarshal(args.input, args.output, args.input_format, args.output_format,
            args.indent_json, args.wrap, args.unwrap)


def remarshal(input, output, input_format, output_format, indent_json=None,
        wrap=None, unwrap=None):
    if input == '-':
        input_file = sys.stdin
    else:
        input_file = open(input, 'rb')

    if output == '-':
        output_file = getattr(sys.stdout, 'buffer', sys.stdout)
    else:
        output_file = open(output, 'wb')

    input_data = input_file.read()

    if input_format == 'json':
        parsed = json.loads(input_data.decode('utf-8'))
    elif input_format == 'toml':
        parsed = pytoml.loads(input_data)
    elif input_format == 'yaml':
        parsed = yaml.load(input_data)
    else:
        raise ValueError('Unknown input format: {0}'.format(input_format))

    if unwrap is not None:
        parsed = parsed[unwrap]
    if wrap is not None:
        temp = {}
        temp[wrap] = parsed
        parsed = temp

    if output_format == 'json':
        if indent_json == True:
            indent_json = 2
        if indent_json:
            separators=(',', ': ')
        else:
            separators=(',', ':')
        output_data = json.dumps(parsed, default=json_serialize,
                                ensure_ascii=False, indent=indent_json,
                                separators=separators, sort_keys=True) + "\n"
    elif output_format == 'toml':
        try:
            output_data = pytoml.dumps(parsed, sort_keys=True)
        except AttributeError as e:
            if str(e) == "'list' object has no attribute 'keys'":
                raise ValueError('cannot convert non-dictionary data to TOML;' +
                        ' use "wrap" to wrap it in a dictionary')
            else:
                raise e
    elif output_format == 'yaml':
        output_data = yaml.safe_dump(parsed, allow_unicode=True,
                                    default_flow_style=False,
                                    encoding=None)
    else:
        raise ValueError('Unknown output format: {0}'.
                format(output_format))
    output_file.write(output_data.encode('utf-8'))

    input_file.close()
    output_file.close()


def main():
    try:
        run(sys.argv)
    except ValueError as e:
        print('Error: {0}'.format(e), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
