from abiflib import ranklist_from_jabmod_voteline
from abiftestfuncs import *
import json

mycols = ['fetchspec', 'filename',
          'votelinenum', 'votelinecandnum', 'votelinecandtok',
          'abif_offset', 'abif_line', 'html_offset', 'html_line']
testdicts = [
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "localabif/electorama-abif/potus1980test01.abif",
        "votelinenum": 0,
        "votelinecandnum": 1,
        "votelinecandtok": "Anderson",
        "abif_offset": -6,
        "abif_line": "20010:Carter>Anderson>Reagan",
        "html_offset": 8,
        "html_line": "     Anderson",
        "id": "ranking_001"
    },
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "localabif/electorama-abif/test001.abif",
        "votelinenum": 1,
        "votelinecandnum": 1,
        "votelinecandtok": "Allie",
        "abif_offset": -3,
        "abif_line": "7:Georgie/5>Allie/4>Dennis/3=Harold/3>Candace/2>Edith/1>Billy=Frank",
        "html_offset": 8,
        "html_line": "     Allie",
        "id": "ranking_002"
    },
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "localabif/electorama-abif/test015.abif",
        "votelinenum": 1,
        "votelinecandnum": 1,
        "votelinecandtok": "DGM",
        "abif_offset": -5,
        "abif_line": "27:DGM/5>SBJ/2>SY/1>AM",
        "html_offset": 8,
        "html_line": "     Doña García Márquez [\"DGM\"]",
        "id": "ranking_003"
    },
    {
        "fetchspec": None,
        "filename": 'testdata/tenn-example/tennessee-example-simple.abif',
        "votelinenum": 3,
        "votelinecandnum": 2,
        "votelinecandtok": "Nash",
        "abif_offset": -2,
        "abif_line": "15:Chat>Knox>Nash>Memph",
        "html_offset": 8,
        "html_line": "     Nash",
        "id": "ranking_004"
    },
]

pytestlist = []
for testdict in testdicts:
    myparam = get_pytest_abif_testsubkey(testdict, cols=mycols)
    pytestlist.append(myparam)


@pytest.mark.parametrize(mycols, pytestlist)
def test_voteline_to_ranking(fetchspec, filename,
                             votelinenum, votelinecandnum, votelinecandtok,
                             abif_offset, abif_line, html_offset, html_line):
    fh = open(filename, 'rb')

    cmd_args = ["-t", "jabmod", filename]
    abiftool_output = get_abiftool_output_as_array(cmd_args)
    jabmod_from_abif = json.loads("\n".join(abiftool_output))
    votelinemod = jabmod_from_abif['votelines'][votelinenum]
    ranklist = ranklist_from_jabmod_voteline(votelinemod)
    print(f"{ranklist=}")

    assert ranklist[votelinecandnum] == votelinecandtok

    cmd_args = ["-t", "abif", filename]
    abiflines = get_abiftool_output_as_array(cmd_args)

    assert abiflines[abif_offset] == abif_line

    cmd_args = ["-t", "html_snippet", filename]
    html_lines = get_abiftool_output_as_array(cmd_args)
    assert html_lines[html_offset] == html_line
