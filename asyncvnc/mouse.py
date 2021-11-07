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

    def _write(self):
        self.writer.write(b'\x05')
        self.writer.write(self.buttons.to_bytes(1, 'big'))
        self.writer.write(self.x.to_bytes(2, 'big'))
        self.writer.write(self.y.to_bytes(2, 'big'))

    @contextmanager
    def hold(self, button: int = 1):
        mask = 1 << button
        self.buttons |= mask
        self._write()
        try:
            yield
        finally:
            self.buttons &= ~mask
            self._write()

    def click(self, button: int = 1):
        """
        Presses and releases a mouse button.
        """

        with self.hold(button):
            pass

    def move(self, x: int, y: int):
        """
        Moves the mouse cursor to the given co-ordinates.
        """
        self.x = x
        self.y = y
        self._write()
