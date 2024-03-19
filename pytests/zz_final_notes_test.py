import pytest

stubs = [
    {"desc":
     "Run fetchmgr.py to gather datafiles for skipped tests above "}
]

@pytest.mark.parametrize("stub_item", stubs)
def test_stubs(stub_item):
    pytest.skip(reason=stub_item['desc'])
    assert False
