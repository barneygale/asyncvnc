from io import BytesIO
from asyncvnc import Clipboard


def test_write():
    clipboard = Clipboard(writer=BytesIO())
    clipboard.write('hello world!')
    assert clipboard.writer.getvalue() == b'\x06\x00\x00\x00\x00\x0chello world!'
