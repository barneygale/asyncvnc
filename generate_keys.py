from tempfile import TemporaryDirectory
from subprocess import run
from pathlib import Path
from pprint import pprint
from re import findall


def main():
    keys = {}

    with TemporaryDirectory() as tempdir:
        run(['git', 'clone', 'https://github.com/freedesktop/xorg-proto-x11proto.git'], cwd=tempdir)
        path = Path(tempdir) / 'xorg-proto-x11proto' / 'keysymdef.h'
        for name, code, char in findall(r'#define XK_(\w+)\s+0x(\w+)(?:\s+/\*\s+U\+(\w+))?', path.read_text()):
            code = int(code, 16)
            if code <= 0xFFFF:
                if char:
                    char = chr(int(char, 16))
                    keys[char] = code
                keys[name] = code

    keys['Del'] = keys['Delete']
    keys['Esc'] = keys['Escape']
    keys['Alt'] = keys['Alt_L']
    keys['Ctrl'] = keys['Control_L']
    keys['Super'] = keys['Super_L']
    keys['Shift'] = keys['Shift_L']
    keys['Backspace'] = keys['BackSpace']

    with Path('asyncvnc', 'keys.py').open('w') as f:
        f.write('# !!! auto-generated; do not edit !!! #\n\n')
        f.write('# flake8: noqa\n')
        f.write('keys = \\\n')
        pprint(keys, f)


if __name__ == '__main__':
    main()
