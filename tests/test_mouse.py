from io import BytesIO
from asyncvnc import Mouse


def test_hold():
    mouse = Mouse(writer=BytesIO())
    with mouse.hold():
        pass
    assert mouse.writer.getvalue() == (
        b'\x05\x01\x00\x00\x00\x00'  # LMB down
        b'\x05\x00\x00\x00\x00\x00'  # LMB up
    )


def test_click():
    mouse = Mouse(writer=BytesIO())
    mouse.click()
    assert mouse.writer.getvalue() == (
        b'\x05\x01\x00\x00\x00\x00'  # LMB down
        b'\x05\x00\x00\x00\x00\x00'  # LMB up
    )


def test_right_click():
    mouse = Mouse(writer=BytesIO())
    mouse.click(2)
    assert mouse.writer.getvalue() == (
        b'\x05\x04\x00\x00\x00\x00'  # RMB down
        b'\x05\x00\x00\x00\x00\x00'  # RMB up
    )


def test_move():
    mouse = Mouse(writer=BytesIO())
    mouse.move(11, 22)
    assert mouse.writer.getvalue() == b'\x05\x00\x00\x0b\x00\x16'
