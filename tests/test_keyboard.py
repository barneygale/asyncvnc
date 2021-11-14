from io import BytesIO
from asyncvnc import Keyboard

import pytest


def test_hold_one():
    keyboard = Keyboard(writer=BytesIO())
    with keyboard.hold('x'):
        pass
    assert keyboard.writer.getvalue() == (
        b'\x04\x01\x00\x00\x00\x00\x00x'
        b'\x04\x00\x00\x00\x00\x00\x00x'
    )


def test_hold_many():
    keyboard = Keyboard(writer=BytesIO())
    with keyboard.hold('Ctrl', 'Alt', 'x'):
        pass

    assert keyboard.writer.getvalue() == (
        b'\x04\x01\x00\x00\x00\x00\xff\xe3'  # Ctrl down
        b'\x04\x01\x00\x00\x00\x00\xff\xe9'  # Alt down
        b'\x04\x01\x00\x00\x00\x00\x00x'  # x down
        b'\x04\x00\x00\x00\x00\x00\x00x'  # x up
        b'\x04\x00\x00\x00\x00\x00\xff\xe9'  # Alt up
        b'\x04\x00\x00\x00\x00\x00\xff\xe3'  # Ctrl up
    )


def test_hold_invalid():
    with pytest.raises(KeyError) as excinfo:
        with Keyboard(writer=BytesIO()).hold('INVALID_KEY'):
            pass
    assert str(excinfo.value) == repr('INVALID_KEY')


def test_press():
    keyboard = Keyboard(writer=BytesIO())
    keyboard.press('Ctrl', 'Alt', 'x')
    assert keyboard.writer.getvalue() == (
        b'\x04\x01\x00\x00\x00\x00\xff\xe3'  # Ctrl down
        b'\x04\x01\x00\x00\x00\x00\xff\xe9'  # Alt down
        b'\x04\x01\x00\x00\x00\x00\x00x'  # x down
        b'\x04\x00\x00\x00\x00\x00\x00x'  # x up
        b'\x04\x00\x00\x00\x00\x00\xff\xe9'  # Alt up
        b'\x04\x00\x00\x00\x00\x00\xff\xe3'  # Ctrl up
    )


def test_write():
    keyboard = Keyboard(writer=BytesIO())
    keyboard.write('abc')
    assert keyboard.writer.getvalue() == (
        b'\x04\x01\x00\x00\x00\x00\x00a'  # a down
        b'\x04\x00\x00\x00\x00\x00\x00a'  # a up
        b'\x04\x01\x00\x00\x00\x00\x00b'  # b down
        b'\x04\x00\x00\x00\x00\x00\x00b'  # b up
        b'\x04\x01\x00\x00\x00\x00\x00c'  # c down
        b'\x04\x00\x00\x00\x00\x00\x00c'  # c up
    )
