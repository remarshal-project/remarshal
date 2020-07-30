#! /usr/bin/env python
# remarshal, a utility to convert between serialization formats.
# Copyright (c) 2014, 2015, 2016, 2017, 2018, 2019, 2020 D. Bohdan
# License: MIT

from .context import remarshal

import collections
import datetime
import errno
import os
import os.path
import re
import sys
import tempfile
import unittest

import cbor2
import pytest

TEST_PATH = os.path.dirname(os.path.realpath(__file__))
PYTHON_3 = True
try:
    unicode
    PYTHON_3 = False
except NameError:
    pass


def data_file_path(filename):
    path_list = [TEST_PATH]
    if re.match(r'example\.(json|msgpack|toml|yaml|cbor)$', filename):
        path_list.append('..')
    path_list.append(filename)
    return os.path.join(*path_list)


def read_file(filename, binary=False):
    with open(data_file_path(filename), 'rb') as f:
        content = f.read()
        if not binary:
            content = content.decode('utf-8')
    return content


def sorted_dict(d):
    return collections.OrderedDict(sorted(d.items()))


def toml_signature(data):
    '''A lossy representation for TOML example data for comparison.'''
    def strip_more(line):
        return re.sub(r' *#.*$', '', line.strip()).replace(' ', '')

    def f(lst):
        def q(line):
            return (
                line.startswith('#') or
                line == u'' or
                line == u']' or
                re.match(r'^".*",?$', line) or
                re.match(r'^hosts', line)
            )
        return sorted(
            [strip_more(line) for line in lst if not q(strip_more(line))]
        )

    return f(data.split("\n"))


def traverse(
    col,
    dict_callback=lambda x: x,
    list_callback=lambda x: x,
    key_callback=lambda x: x,
    value_callback=lambda x: x
):
    if isinstance(col, dict):
        return dict_callback(col.__class__([
            (key_callback(k), traverse(
                v,
                dict_callback,
                list_callback,
                key_callback,
                value_callback
            )) for (k, v) in col.items()
        ]))
    elif isinstance(col, list):
        return list_callback([traverse(
            x,
            dict_callback,
            list_callback,
            key_callback,
            value_callback
        ) for x in col])
    else:
        return value_callback(col)


class TestRemarshal(unittest.TestCase):

    def temp_filename(self):
        fd, temp_filename = tempfile.mkstemp()
        os.close(fd)
        self.temp_files.append(temp_filename)
        return temp_filename

    def assert_cbor_same(self, output, reference):
        # To date, Python's CBOR libraries don't support encoding to
        # canonical-form CBOR, so we have to parse and deep-compare.
        output_dec = cbor2.loads(output)
        reference_dec = cbor2.loads(reference)
        assert output_dec == reference_dec

    def convert_and_read(
        self,
        input,
        input_format,
        output_format,
        wrap=None,
        unwrap=None,
        indent_json=True,
        yaml_options={},
        ordered=False,
        binary=False,
        transform=None,
    ):
        output_filename = self.temp_filename()
        remarshal.remarshal(
            data_file_path(input),
            output_filename,
            input_format,
            output_format,
            wrap=wrap,
            unwrap=unwrap,
            indent_json=indent_json,
            yaml_options=yaml_options,
            ordered=ordered,
            transform=transform
        )
        return read_file(output_filename, binary)

    def setUp(self):
        self.maxDiff = None
        self.temp_files = []

    def tearDown(self):
        for filename in self.temp_files:
            os.remove(filename)

    def test_json2json(self):
        output = self.convert_and_read('example.json', 'json', 'json')
        reference = read_file('example.json')
        assert output == reference

    def test_msgpack2msgpack(self):
        output = self.convert_and_read(
            'example.msgpack',
            'msgpack',
            'msgpack',
            binary=True,
            ordered=True,
        )
        reference = read_file('example.msgpack', binary=True)
        assert output == reference

    def test_toml2toml(self):
        output = self.convert_and_read('example.toml', 'toml', 'toml')
        reference = read_file('example.toml')
        assert toml_signature(output) == toml_signature(reference)

    def test_yaml2yaml(self):
        output = self.convert_and_read('example.yaml', 'yaml', 'yaml')
        reference = read_file('example.yaml')
        assert output == reference

    def test_cbor2cbor(self):
        output = self.convert_and_read(
            'example.cbor',
            'cbor',
            'cbor',
            binary=True
        )
        reference = read_file('example.cbor', binary=True)
        self.assert_cbor_same(output, reference)

    def test_json2msgpack(self):
        def patch(x):
            x['owner']['dob'] = datetime.datetime(1979, 5, 27, 7, 32)
            return x

        output = self.convert_and_read(
            'example.json',
            'json',
            'msgpack',
            binary=True,
            ordered=True,
            transform=patch,
        )
        reference = read_file('example.msgpack', binary=True)
        assert output == reference

    @unittest.skipUnless(PYTHON_3, 'requires Python 3')
    def test_json2cbor(self):
        def patch(x):
            x['owner']['dob'] = datetime.datetime(
                1979, 5, 27,
                7, 32, 0, 0,
                datetime.timezone.utc
            )
            return x

        output = self.convert_and_read(
            'example.json',
            'json',
            'cbor',
            binary=True,
            ordered=True,
            transform=patch,
        )

        reference = read_file('example.cbor', binary=True)
        self.assert_cbor_same(output, reference)

    def test_json2toml(self):
        output = self.convert_and_read('example.json', 'json', 'toml')
        reference = read_file('example.toml')
        output_sig = toml_signature(output)
        # The date in 'example.json' is a string.
        reference_sig = toml_signature(
            reference.replace(
                '1979-05-27T07:32:00Z',
                '"1979-05-27T07:32:00+00:00"'
            )
        )
        assert output_sig == reference_sig

    def test_json2yaml(self):
        output = self.convert_and_read('example.json', 'json', 'yaml')
        reference = read_file('example.yaml')
        # The date in 'example.json' is a string.
        reference_patched = reference.replace(
            '1979-05-27 07:32:00+00:00',
            "'1979-05-27T07:32:00+00:00'"
        )
        assert output == reference_patched

    def test_msgpack2json(self):
        output = self.convert_and_read('example.msgpack', 'msgpack', 'json')
        reference = read_file('example.json')
        assert output == reference

    def test_msgpack2toml(self):
        output = self.convert_and_read('example.msgpack', 'msgpack', 'toml')
        reference = read_file('example.toml')
        assert toml_signature(output) == toml_signature(reference)

    def test_msgpack2yaml(self):
        output = self.convert_and_read('example.msgpack', 'msgpack', 'yaml')
        reference = read_file('example.yaml')
        assert output == reference

    def test_msgpack2cbor(self):
        output = self.convert_and_read(
            'example.msgpack', 'msgpack', 'cbor',
            binary=True,
        )
        reference = read_file('example.cbor', binary=True)
        self.assert_cbor_same(output, reference)

    def test_toml2json(self):
        output = self.convert_and_read('example.toml', 'toml', 'json')
        reference = read_file('example.json')
        assert output == reference

    def test_toml2msgpack(self):
        output = self.convert_and_read(
            'example.toml',
            'toml',
            'msgpack',
            binary=True,
            transform=lambda col: traverse(
                col,
                dict_callback=sorted_dict
            ),
        )
        reference = read_file('example.msgpack', binary=True)
        assert output == reference

    def test_toml2yaml(self):
        output = self.convert_and_read('example.toml', 'toml', 'yaml')
        reference = read_file('example.yaml')
        assert output == reference

    def test_toml2cbor(self):
        output = self.convert_and_read(
            'example.toml', 'toml', 'cbor',
            binary=True,
        )
        reference = read_file('example.cbor', binary=True)
        self.assert_cbor_same(output, reference)

    def test_yaml2json(self):
        output = self.convert_and_read('example.yaml', 'yaml', 'json')
        reference = read_file('example.json')
        assert output == reference

    def test_yaml2msgpack(self):
        output = self.convert_and_read(
            'example.yaml',
            'yaml',
            'msgpack',
            ordered=True,
            binary=True,
        )
        reference = read_file('example.msgpack', binary=True)
        assert output == reference

    def test_yaml2toml(self):
        output = self.convert_and_read('example.yaml', 'yaml', 'toml')
        reference = read_file('example.toml')
        assert toml_signature(output) == toml_signature(reference)

    def test_yaml2cbor(self):
        output = self.convert_and_read(
            'example.yaml', 'yaml', 'cbor',
            binary=True,
        )
        reference = read_file('example.cbor', binary=True)
        self.assert_cbor_same(output, reference)

    def test_cbor2json(self):
        output = self.convert_and_read('example.cbor', 'cbor', 'json')
        reference = read_file('example.json')
        assert output == reference

    def test_cbor2toml(self):
        output = self.convert_and_read('example.cbor', 'cbor', 'toml')
        reference = read_file('example.toml')
        output_sig = toml_signature(output)
        reference_sig = toml_signature(reference)
        assert output_sig == reference_sig

    def test_cbor2yaml(self):
        output = self.convert_and_read('example.cbor', 'cbor', 'yaml')
        reference = read_file('example.yaml')
        assert output == reference

    def test_cbor2msgpack(self):
        output = self.convert_and_read(
            'example.cbor',
            'cbor',
            'msgpack',
            binary=True,
            ordered=True,
            transform=lambda col: traverse(
                col,
                dict_callback=sorted_dict
            ),
        )
        reference = read_file('example.msgpack', binary=True)
        assert output == reference

    def test_missing_wrap(self):
        with pytest.raises(ValueError) as context:
            output = self.convert_and_read('array.json', 'json', 'toml')

    def test_wrap(self):
        output = self.convert_and_read('array.json', 'json', 'toml',
                                       wrap='data')
        reference = read_file('array.toml')
        assert output == reference

    def test_unwrap(self):
        output = self.convert_and_read('array.toml', 'toml', 'json',
                                       unwrap='data',
                                       indent_json=None)
        reference = read_file('array.json')
        assert output == reference

    def test_malformed_json(self):
        with pytest.raises(ValueError) as context:
            self.convert_and_read('garbage', 'json', 'yaml')

    def test_malformed_toml(self):
        with pytest.raises(ValueError) as context:
            self.convert_and_read('garbage', 'toml', 'yaml')

    def test_malformed_yaml(self):
        with pytest.raises(ValueError) as context:
            self.convert_and_read('garbage', 'yaml', 'json')

    @unittest.skipUnless(PYTHON_3, 'requires Python 3')
    def test_binary_to_json(self):
        with pytest.raises(ValueError) as context:
            self.convert_and_read('bin.msgpack', 'msgpack', 'json')
        with pytest.raises(ValueError) as context:
            self.convert_and_read('bin.yml', 'yaml', 'json')

    @unittest.skipUnless(PYTHON_3, 'requires Python 3')
    def test_binary_to_msgpack(self):
        self.convert_and_read('bin.yml', 'yaml', 'msgpack', binary=True)

    @unittest.skipUnless(PYTHON_3, 'requires Python 3')
    def test_binary_to_toml(self):
        with pytest.raises(ValueError) as context:
            self.convert_and_read('bin.msgpack', 'msgpack', 'toml')
        with pytest.raises(ValueError) as context:
            self.convert_and_read('bin.yml', 'yaml', 'toml')

    @unittest.skipUnless(PYTHON_3, 'requires Python 3')
    def test_binary_to_yaml(self):
        self.convert_and_read('bin.msgpack', 'msgpack', 'yaml')

    @unittest.skipUnless(PYTHON_3, 'requires Python 3')
    def test_binary_to_cbor(self):
        self.convert_and_read('bin.msgpack', 'msgpack', 'cbor', binary=True)

    def test_yaml_style_default(self):
        output = self.convert_and_read('long-line.json', 'json', 'yaml')
        reference = read_file('long-line-default.yaml')
        assert output == reference

    def test_yaml_style_single_quote(self):
        output = self.convert_and_read(
            'long-line.json',
            'json',
            'yaml',
            yaml_options={'default_style': "'"}
        )
        reference = read_file('long-line-single-quote.yaml')
        assert output == reference

    def test_yaml_style_double_quote(self):
        output = self.convert_and_read(
            'long-line.json',
            'json',
            'yaml',
            yaml_options={'default_style': '"'}
        )
        reference = read_file('long-line-double-quote.yaml')
        assert output == reference

    def test_yaml_style_pipe(self):
        output = self.convert_and_read(
            'long-line.json',
            'json',
            'yaml',
            yaml_options={'default_style': '|'}
        )
        reference = read_file('long-line-pipe.yaml')
        assert output == reference

    def test_yaml_style_gt(self):
        output = self.convert_and_read(
            'long-line.json',
            'json',
            'yaml',
            yaml_options={'default_style': '>'}
        )
        reference = read_file('long-line-gt.yaml')
        assert output == reference

    def test_argv0_to_format(self):
        def test_format_string(s):
            for from_str in 'json', 'toml', 'yaml':
                for to_str in 'json', 'toml', 'yaml':
                    found, from_parsed, to_parsed = remarshal.argv0_to_format(
                        s.format(from_str, to_str)
                    )
                    assert (found, from_parsed, to_parsed) == \
                        (found, from_str, to_str)

        test_format_string('{0}2{1}')
        test_format_string('{0}2{1}.exe')
        test_format_string('{0}2{1}-script.py')

    def test_format_detection(self):
        ext_to_fmt = {
            'json': 'json',
            'toml': 'toml',
            'yaml': 'yaml',
            'yml': 'yaml',
        }

        for from_ext in ext_to_fmt.keys():
            for to_ext in ext_to_fmt.keys():
                args = remarshal.parse_command_line([
                    sys.argv[0],
                    'input.' + from_ext,
                    'output.' + to_ext
                ])

                assert args.input_format == ext_to_fmt[from_ext]
                assert args.output_format == ext_to_fmt[to_ext]

    def test_format_detection_failure_input_stdin(self):
        with pytest.raises(SystemExit) as cm:
            remarshal.parse_command_line([sys.argv[0], '-'])
        assert cm.value.code == 2

    def test_format_detection_failure_input_txt(self):
        with pytest.raises(SystemExit) as cm:
            remarshal.parse_command_line([sys.argv[0], 'input.txt'])
        assert cm.value.code == 2

    def test_format_detection_failure_output_txt(self):
        with pytest.raises(SystemExit) as cm:
            remarshal.parse_command_line([
                sys.argv[0],
                'input.json',
                'output.txt'
            ])
        assert cm.value.code == 2

    def test_run_no_args(self):
        with pytest.raises(SystemExit) as cm:
            remarshal.run([sys.argv[0]])
        assert cm.value.code == 2

    def test_run_help(self):
        with pytest.raises(SystemExit) as cm:
            remarshal.run([sys.argv[0], '--help'])
        assert cm.value.code == 0

    def test_run_no_input_file(self):
        with pytest.raises(IOError) as cm:
            args = [
                sys.argv[0],
                '-if',
                'json',
                '-of',
                'json',
                'fake-input-file-that-almost-certainly-doesnt-exist-2382'
            ]
            remarshal.run(args)
        assert cm.value.errno == errno.ENOENT

    def test_run_no_output_dir(self):
        with pytest.raises(IOError) as cm:
            args = [
                sys.argv[0],
                '-if',
                'json',
                '-of',
                'json',
                '-o',
                'this_path/almost-certainly/doesnt-exist-5836',
                data_file_path('example.json')
            ]
            remarshal.run(args)
        assert cm.value.errno == errno.ENOENT

    def test_run_no_output_format(self):
        with pytest.raises(SystemExit) as cm:
            remarshal.run([sys.argv[0], data_file_path('array.toml')])
        assert cm.value.code == 2

    def test_ordered_simple(self):
        for from_ in 'json', 'toml', 'yaml':
            for to in 'json', 'toml', 'yaml':
                output = self.convert_and_read(
                    'order.' + from_,
                    from_,
                    to,
                    ordered=True
                )
                reference = read_file('order.' + to)
                assert output == reference

    def test_ordered_yaml2yaml(self):
        output = self.convert_and_read(
            'example.yaml',
            'yaml',
            'yaml',
            ordered=True
        )
        reference = read_file('example.yaml')
        assert output == reference
