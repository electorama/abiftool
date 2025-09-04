# Testing Infrastructure

## Overview

The abiftool test suite is located in `abiftool/pytests/` (as opposed to "tests").

## Test Organization

### Core Test Structure

Tests follow a parametrized pattern using `pytest.param()` with descriptive IDs:

```python
testlist = [
    pytest.param(
        ['-f', 'abif', '-t', 'json', '-m', 'approval'],  # CLI options
        'testdata/mock-elections/tennessee-example-approval.abif',  # input file
        'is_equal',  # test type
        ["approval_counts", "Nash"],  # data path
        50,  # expected value
        id='approval_001'  # descriptive test ID
    ),
]

@pytest.mark.parametrize("options,filename,test_type,test_data,expected", testlist)
def test_approval_functionality(options, filename, test_type, test_data, expected):
    # Test implementation using abiftestfuncs helpers
```

### Test Categories by File

#### Core Functionality
- **`core_test.py`** - ABIF format parsing, JABMOD roundtripping, SF CVR format, candidate name handling
- **`codefmt_test.py`** - PEP8 compliance checking for all Python files (critical for code quality)
- **`cli_test.py`** - Command-line interface testing and error handling
- **`ballot_test.py`** - Ballot parsing and validation logic

#### Voting Methods
- **`approval_test.py`** - Approval voting with native choose_many ballots
- **`irv_test.py`** - Instant Runoff Voting with ranked choice ballots
- **`fptp_test.py`** - First Past The Post voting
- **`scorestar_test.py`** - STAR voting (Score Then Automatic Runoff)
- **`pairwise_test.py`** - Pairwise comparisons and Condorcet methods
- **`starcount_test.py`** - STAR vote counting and scoring logic

#### Format Converters
- **`sftxt_test.py`** - San Francisco text format conversion
- **`preflib_test.py`** - PrefLib format support
- **`debvote_test.py`** - Debian voting format
- **`questionable_input_test.py`** - Edge cases and malformed input handling

#### Data Processing & Utilities
- **`ranking_test.py`** - Ranking logic and preference handling
- **`nameq_test.py`** - Name normalization and candidate matching
- **`roundtrip_test.py`** - Format conversion roundtripping
- **`html_test.py`** - HTML output generation for web interface
- **`texttable_test.py`** - Text table formatting
- **`vizelect_test.py`** - Election visualization logic
- **`linecount_test.py`** - Line counting utilities
- **`abifprefstr_test.py`** - Preference string parsing

### Test Support Infrastructure

#### `conftest.py`
Provides pytest configuration and post-test hooks:
- **Data file guidance**: Reminds users to run `./fetchmgr.py` for missing test data
- **Missing library detection**: Reports missing dependencies from `requirements.txt`
- **Development logging**: Collects and displays development tool messages

#### `abiftestfuncs.py`
Central testing utilities and helper functions:
- **`get_abiftool_scriptloc()`** - Locates abiftool.py executable
- **`get_abiftool_output_as_array()`** - Runs CLI commands and captures output
- **CLI execution helpers** - Standardized command running and output parsing
- **Test data management** - File path resolution and test data access

### Test Data Dependencies

Many tests depend on external election data files that must be fetched:

```bash
# Fetch all test data files
./fetchmgr.py fetchspecs/*

# Run tests (many will be skipped without data)
pytest

# Run tests with caching for performance
AWT_PYTEST_CACHING=filesystem pytest
```


## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run specific test module
pytest pytests/approval_test.py

# Run with verbose output
pytest -v

# Filter by test pattern
pytest -k approval

# Performance testing with caching
AWT_PYTEST_CACHING=filesystem pytest
```

### Critical Quality Checks
```bash
# ALWAYS run before declaring work complete
pytest pytests/codefmt_test.py -v

# Alternative PEP8 checking for specific files
pycodestyle abiflib/approval_tally.py --max-line-length=79 --ignore=E501,W504
```

### Environment Variables

- **`AWT_PYTEST_CACHING`** - Controls test caching (`none`, `simple`, `filesystem`)
- Test data availability affects skip patterns - many tests skip if data files missing

## Test Data Management

### Test Data Sources
- **Local files**: `testdata/` directory with minimal election examples
- **External data**: Requires fetchmgr.py to download real election data
- **Mock elections**: Synthetic data for testing specific scenarios

### Test Data Organization
Tests reference data via relative paths from abiftool directory:
- `testdata/mock-elections/` - Synthetic test elections
- `testdata/real-elections/` - Historical election data
- Format-specific subdirectories for different data sources

## Testing Best Practices

### Test Structure
- **Parametrized tests preferred** - Use single test function with `pytest.param()` lists
- **Descriptive IDs** - Format: `{module}_{NNN}[_optional_descriptor]`
- **Focused assertions** - Test one specific behavior per test case
- **Data-driven testing** - External test data over hardcoded values

### Code Quality
- **PEP8 compliance mandatory** - `codefmt_test.py` must pass before completing work
- **Import organization** - Standard library, external packages, internal modules
- **Error handling** - Test both success and failure conditions
- **Regression protection** - Ensure existing tests remain stable during changes
