from asyncio import StreamWriter
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Mouse:
    """
    The virtual mouse.
    """

    writer: StreamWriter = field(repr=False)
    buttons: int = 0
    x: int = 0
    y: int = 0

    def _update(self):
        self.writer.write(b'\x05')
        self.writer.write(self.buttons.to_bytes(1, 'big'))
        self.writer.write(self.x.to_bytes(2, 'big'))
        self.writer.write(self.y.to_bytes(2, 'big'))

    @contextmanager
    def _hold(self, button):
        self.buttons |= button
        self._update()
        try:
            yield
        finally:
            self.buttons &= ~button
            self._update()

    def move(self, x: int, y: int):
        """
        Moves the mouse cursor to the given co-ordinates.
        """
        self.x = x
        self.y = y
        self._update()

    @contextmanager
    def hold(self):
        """
        Context manager that presses the left mouse button on enter, and releases it on exit.
        """

        with self._hold(1):
            yield

    def click(self):
        """
        Presses and releases the left mouse button.
        """

        with self._hold(1):
            pass

    def middle_click(self):
        """
        Presses and releases the middle mouse button.
        """

        with self._hold(2):
            pass

    def right_click(self):
        """
        Presses and releases the right mouse button.
        """

        with self._hold(4):
            pass

    def scroll_up(self):
        """
        Scrolls up with the mouse wheel.
        """

        with self._hold(8):
            pass

    def scroll_down(self):
        """
        Scrolls down with the mouse wheel.
        """

        with self._hold(16):
            pass
