from asyncio import StreamWriter
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Flag


class MouseButton(Flag):
    """
    Mouse button state.
    """

    #: No mouse button
    NONE = 0

    #: Left mouse button
    LEFT = 1

    #: Middle mouse button
    MIDDLE = 2

    #: Right mouse button
    RIGHT = 4

    #: Scroll up
    SCROLL_UP = 8

    #: Scroll down
    SCROLL_DOWN = 16


@dataclass
class Mouse:
    """
    The virtual mouse.
    """

    writer: StreamWriter = field(repr=False)
    _buttons: MouseButton = MouseButton.NONE
    _x: int = 0
    _y: int = 0

    def _update(self):
        self.writer.write(b'\x05')
        self.writer.write(self._buttons.value.to_bytes(1, 'big'))
        self.writer.write(self._x.to_bytes(2, 'big'))
        self.writer.write(self._y.to_bytes(2, 'big'))

    def move(self, x: int, y: int):
        self._x = x
        self._y = y
        self._update()

    @contextmanager
    def hold(self, button: MouseButton = MouseButton.LEFT):
        self._buttons |= button
        self._update()
        try:
            yield
        finally:
            self._buttons &= ~button
            self._update()

    def click(self, button: MouseButton = MouseButton.LEFT):
        with self.hold(button):
            pass

    def middle_click(self):
        self.click(MouseButton.MIDDLE)

    def right_click(self):
        self.click(MouseButton.RIGHT)

    def scroll_up(self):
        self.click(MouseButton.SCROLL_UP)

    def scroll_down(self):
        self.click(MouseButton.SCROLL_DOWN)
