import atexit
from abiflib import LogfileSingleton

def postmortem(session=None, terminalreporter=None, exitstatus=None, config=None):
    '''postmortem is based on a hack documented on StackOverflow
    https://stackoverflow.com/a/38806934/362951'''

    num_skipped = len(terminalreporter.stats.get('skipped', []))
    if num_skipped > 0:
        print("Run fetchmgr.py to gather datafiles for skipped tests above")
    logobj = LogfileSingleton()
    for msg in logobj.devtoolmsgs:
        print(msg)


#def pytest_sessionfinish(session, exitstatus):
#    atexit.register(postmortem, session=session, exitstatus=exitstatus)
#    print("Hello from `pytest_sessionfinish` hook!")
#    print(f"Exit status: {exitstatus}")

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    atexit.register(postmortem, terminalreporter=terminalreporter,
                    exitstatus=exitstatus, config=config)
