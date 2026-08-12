#!/usr/bin/env python3
import sys, re

def main():
    for f in sys.argv[1:]:
        with open(f) as fp:
            content = fp.read()
        if '_ignoreVanilla: true' not in content:
            print(f'MISSING _ignoreVanilla: {f}')
            return 1
        if 'STRUCTURE_EXPLANATION' not in content:
            print(f'MISSING STRUCTURE_EXPLANATION: {f}')
            return 1
    print('All data files have required headers')
    return 0

if __name__ == '__main__':
    sys.exit(main())
