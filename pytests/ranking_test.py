from abiflib import ranklist_from_jabmod_voteline
from abiftestfuncs import *
import json

mycols = ['fetchspec', 'filename',
          'votelinenum', 'votelinecandnum', 'votelinecandtok',
          'abif_offset', 'abif_line', 'html_offset', 'html_line']
testdicts = [
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "testdata/electorama-abif/testfiles/potus1980test01.abif",
        "votelinenum": 0,
        "votelinecandnum": 1,
        "votelinecandtok": "Anderson",
        "abif_offset": -7,
        "abif_line": "20010:Carter>Anderson>Reagan",
        "html_offset": 6,
        "html_line": "   Anderson"
    },
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "testdata/electorama-abif/testfiles/test001.abif",
        "votelinenum": 1,
        "votelinecandnum": 1,
        "votelinecandtok": "Allie",
        "abif_offset": -4,
        "abif_line": "7:Georgie/5>Allie/4>Dennis/3=Harold/3>Candace/2>Edith/1>Billy/0=Frank/0",
        "html_offset": 6,
        "html_line": "   Allie"
    },
    {
        "fetchspec": "abif-electorama.fetchspec.json",
        "filename": "testdata/electorama-abif/testfiles/test015.abif",
        "votelinenum": 1,
        "votelinecandnum": 1,
        "votelinecandtok": "DGM",
        "abif_offset": -6,
        "abif_line": "27:DGM/5>SBJ/2>SY/1>AM/0",
        "html_offset": 6,
        "html_line": "   Doña García Márquez [\"DGM\"]"
    }
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

    jabmodstr_from_abif = \
        subprocess.run(["abiftool.py", "-t", "jabmod", filename],
                       capture_output=True,
                       text=True).stdout
    jabmod_from_abif = json.loads(jabmodstr_from_abif)
    votelinemod = jabmod_from_abif['votelines'][votelinenum]
    ranklist = ranklist_from_jabmod_voteline(votelinemod)

    assert ranklist[votelinecandnum] == votelinecandtok

    abifstr_from_abiftool = \
        subprocess.run(["abiftool.py", "-t", "abif", filename],
                       capture_output=True,
                       text=True).stdout
    abiflines = abifstr_from_abiftool.split("\n")

    assert abiflines[abif_offset] == abif_line

    errorobj  = \
        subprocess.run(["abiftool.py", "-t", "html_snippet", filename],
                       capture_output=True,
                       text=True)
    html_from_abiftool = errorobj.stdout
    html_lines = html_from_abiftool.split("\n")

    assert html_lines[html_offset] == html_line
