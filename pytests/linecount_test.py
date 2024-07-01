from abiftestfuncs import *
import pytest
from subprocess import run, PIPE
@pytest.mark.parametrize(
    'input_file, command_line_args, expected_output_length',
    [
        ('testdata/widjexample/widjexample.jabmod', ['-t', 'abif'], 22),
        ('testdata/burl2009/burl2009.abif', ['-t', 'jabmod'], 8650),
        ('testdata/burl2009/burl2009.abif', ['-t', 'text'], 26)
    ]
)

def test_abiftool_linecount(input_file, command_line_args, expected_output_length):
    cmd_args = command_line_args + [ input_file ]
    output_lines = get_abiftool_output_as_array(cmd_args)

    # Assert the output length matches the expected length
    assert len(output_lines) == expected_output_length
