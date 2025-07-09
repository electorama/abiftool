import pytest
import subprocess
import os
from pytests.abiftestfuncs import get_abiftool_scriptloc

# TODO: This function largely duplicates get_abiftool_output_as_array in abiftestfuncs.py.
# It should be merged into abiftestfuncs.py to avoid duplication and provide a more
# comprehensive utility for CLI testing (capturing stdout, stderr, and returncode).
def get_abiftool_cli_output(cmd_args):
    """
    Runs abiftool.py with the given command-line arguments and captures its stdout, stderr, and return code.
    """
    command = [get_abiftool_scriptloc(), *cmd_args]
    completed_process = subprocess.run(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       text=True,
                                       check=False) # Do not raise CalledProcessError for non-zero exit codes
    return {
        "stdout": completed_process.stdout,
        "stderr": completed_process.stderr,
        "returncode": completed_process.returncode
    }

test_cases = [
    # No parameters
    pytest.param([], "Missing input file.", "usage:", 2,
                 id="cli_no_params_error"),
]

@pytest.mark.parametrize(
    "cmd_args, expected_error_part, expected_usage_part, expected_returncode",
    test_cases
)
def test_cli_no_params_error(cmd_args, expected_error_part, expected_usage_part, expected_returncode):
    """
    Test abiftool.py when run with no parameters, expecting a usage error.
    """
    result = get_abiftool_cli_output(cmd_args)

    assert result["returncode"] == expected_returncode
    assert expected_error_part in result["stderr"]
    assert expected_usage_part in result["stderr"]
