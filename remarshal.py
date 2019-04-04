#! /usr/bin/env python
# remarshal, a utility to convert between serialization formats.
# Copyright (c) 2014, 2015, 2016, 2017, 2018, 2019 dbohdan
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

from collections import OrderedDict


__version__ = '0.9.1'

FORMATS = ['json', 'toml', 'yaml']
if hasattr(json, 'JSONDecodeError'):
    JSONDecodeError = json.JSONDecodeError
else:
    JSONDecodeError = ValueError


# An OrderedDict loader and dumper for PyYAML.
class OrderedLoader(yaml.SafeLoader):
    pass


class OrderedDumper(yaml.SafeDumper):
    pass


def mapping_constructor(loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


def dict_representer(dumper, data):
    return dumper.represent_mapping(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        data.items()
    )


OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                              mapping_constructor)
OrderedDumper.add_representer(OrderedDict,
                              dict_representer)


# Fix loss of time zone information in PyYAML.
# http://stackoverflow.com/questions/13294186/can-pyyaml-parse-iso8601-dates
class TimezoneLoader(yaml.SafeLoader):
    pass


def timestamp_constructor(loader, node):
    return dateutil.parser.parse(node.value)


for loader in [OrderedLoader, TimezoneLoader]:
    loader.add_constructor(u'tag:yaml.org,2002:timestamp',
                           timestamp_constructor)


def filename2format(filename):
    possible_format = '(' + '|'.join(FORMATS) + ')'
    match = re.search('^' + possible_format + '2' + possible_format, filename)
    if match:
        from_, to = match.groups()
        return True, from_, to
    else:
        return False, None, None


def json_serialize(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError("{0} is not JSON-serializable".format(repr(obj)))


def parse_command_line(argv):
    me = os.path.basename(argv[0])
    format_from_filename, from_, to = filename2format(me)

    parser = argparse.ArgumentParser(description='Convert between TOML, YAML '
                                     'and JSON.')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--input',
                       dest='input_flag',
                       metavar='INPUT',
                       default=None,
                       help='input file')
    group.add_argument('inputfile',
                       nargs='?',
                       default='-',
                       help='input file')

    parser.add_argument('-o', '--output',
                        dest='output',
                        default='-',
                        help='output file')
    if not format_from_filename:
        parser.add_argument('-if', '--input-format',
                            dest='input_format',
                            required=True,
                            help="input format",
                            choices=FORMATS)
        parser.add_argument('-of', '--output-format',
                            dest='output_format',
                            required=True,
                            help="output format",
                            choices=FORMATS)
    if not format_from_filename or to == 'json':
        parser.add_argument('--indent-json',
                            dest='indent_json',
                            action='store_const',
                            const=2,
                            default=None,
                            help='indent JSON output')
    if not format_from_filename or to == 'yaml':
        parser.add_argument('--yaml-style',
                            dest='yaml_style',
                            default=None,
                            help='YAML formatting style',
                            choices=['', '\'', '"', '|', '>'])
    parser.add_argument('--wrap',
                        dest='wrap',
                        default=None,
                        help='wrap the data in a map type with the given key')
    parser.add_argument('--unwrap',
                        dest='unwrap',
                        default=None,
                        help='only output the data stored under the given key')
    parser.add_argument('--preserve-key-order',
                        dest='ordered',
                        action='store_true',
                        help='preserve the order of dictionary/mapping keys')
    parser.add_argument('-v', '--version',
                        action='version',
                        version=__version__)

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
        if to != 'yaml':
            args.__dict__['yaml_style'] = None
    args.__dict__['yaml_options'] = {'default_style': args.yaml_style}
    del args.__dict__['yaml_style']

    return args


def run(argv):
    args = parse_command_line(argv)
    remarshal(args.input,
              args.output,
              args.input_format,
              args.output_format,
              args.wrap,
              args.unwrap,
              args.indent_json,
              args.yaml_options,
              args.ordered)


def remarshal(input,
              output,
              input_format,
              output_format,
              wrap=None,
              unwrap=None,
              indent_json=None,
              yaml_options={},
              ordered=False):
    try:
        if input == '-':
            input_file = getattr(sys.stdin, 'buffer', sys.stdin)
        else:
            input_file = open(input, 'rb')

        if output == '-':
            output_file = getattr(sys.stdout, 'buffer', sys.stdout)
        else:
            output_file = open(output, 'wb')

        input_data = input_file.read()

        if input_format == 'json':
            try:
                pairs_hook = OrderedDict if ordered else dict
                parsed = json.loads(input_data.decode('utf-8'),
                                    object_pairs_hook=pairs_hook)
            except JSONDecodeError as e:
                raise ValueError('Cannot parse as JSON ({0})'.format(e))
        elif input_format == 'toml':
            try:
                pairs_hook = OrderedDict if ordered else dict
                parsed = pytoml.loads(input_data,
                                      object_pairs_hook=pairs_hook)
            except pytoml.core.TomlError as e:
                raise ValueError('Cannot parse as TOML ({0})'.format(e))
        elif input_format == 'yaml':
            try:
                loader = OrderedLoader if ordered else TimezoneLoader
                parsed = yaml.load(input_data,
                                   loader)
            except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
                raise ValueError('Cannot parse as YAML ({0})'.format(e))
        else:
            raise ValueError('Unknown input format: {0}'.format(input_format))

        if unwrap is not None:
            parsed = parsed[unwrap]
        if wrap is not None:
            temp = {}
            temp[wrap] = parsed
            parsed = temp

        if output_format == 'json':
            if indent_json is True:
                indent_json = 2
            if indent_json:
                separators = (',', ': ')
            else:
                separators = (',', ':')
            output_data = json.dumps(parsed,
                                     default=json_serialize,
                                     ensure_ascii=False,
                                     indent=indent_json,
                                     separators=separators,
                                     sort_keys=not ordered) + "\n"
        elif output_format == 'toml':
            try:
                output_data = pytoml.dumps(parsed,
                                           sort_keys=not ordered)
            except AttributeError as e:
                if str(e) == "'list' object has no attribute 'keys'":
                    raise ValueError('Cannot convert non-dictionary data to '
                                     'TOML; use "wrap" to wrap it in a '
                                     'dictionary')
                else:
                    raise e
        elif output_format == 'yaml':
            dumper = OrderedDumper if ordered else yaml.SafeDumper
            output_data = yaml.dump(parsed,
                                    None,
                                    dumper,
                                    allow_unicode=True,
                                    default_flow_style=False,
                                    encoding=None,
                                    **yaml_options)
        else:
            raise ValueError('Unknown output format: {0}'.
                             format(output_format))
        output_file.write(output_data.encode('utf-8'))
        output_file.close()
    finally:
        if 'input_file' in locals():
            input_file.close()
        if 'output_file' in locals():
            output_file.close()


def main():
    try:
        run(sys.argv)
    except KeyboardInterrupt as e:
        pass
    except (IOError, ValueError) as e:
        print('Error: {0}'.format(e), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
