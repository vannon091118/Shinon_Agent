#!/usr/bin/env python3
import sys

def main():
    for f in sys.argv[1:]:
        with open(f) as fp:
            content = fp.read()
        if 'package ' not in content:
            print(f'MISSING package declaration: {f}')
            return 1
    print('All Java files have basic structure')
    return 0

if __name__ == '__main__':
    sys.exit(main())
