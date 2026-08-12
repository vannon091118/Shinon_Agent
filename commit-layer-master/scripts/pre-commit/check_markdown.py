#!/usr/bin/env python3
import sys

def main():
    for f in sys.argv[1:]:
        with open(f) as fp:
            content = fp.read().strip()
        if not content:
            print(f'EMPTY: {f}')
            return 1
        if len(content) < 100:
            print(f'TOO_SHORT: {f} ({len(content)} chars)')
            return 1
    print('All markdown files have substantial content')
    return 0

if __name__ == '__main__':
    sys.exit(main())
