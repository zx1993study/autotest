import sys
from run import main

if __name__ == '__main__':
    result = main(['--case', '32', *sys.argv[1:]])
    raise SystemExit(0 if result['status'] == 'passed' else 2 if result['status'] == 'blocked' else 1)
