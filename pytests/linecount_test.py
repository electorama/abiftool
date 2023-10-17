import pytest
from subprocess import run, PIPE

@pytest.mark.parametrize(
    'input_file, command_line_args, expected_output_length',
    [
        ('testdata/widjexample/widjexample.jabmod', ['-t', 'abif'], 22),
        ('testdata/burl2009/burl2009.abif', ['-t', 'jabmod'], 10233),
        ('testdata/burl2009/burl2009.abif', ['-t', 'texttable'], 18)
    ]
)

def test_abiftool_linecount(input_file, command_line_args, expected_output_length):
    command = ['python3', 'abiftool.py', *command_line_args, input_file]
    completed_process = run(command, stdout=PIPE, text=True)

    # Get the captured output and count the lines
    output_lines = completed_process.stdout.splitlines()

    # Assert the output length matches the expected length
    assert len(output_lines) == expected_output_length
