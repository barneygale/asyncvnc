from asyncio import StreamWriter
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Keyboard:
    """
    The virtual keyboard.
    """

    writer: StreamWriter = field(repr=False)

    def down(self, key: int) -> None:
        """
        Presses a key.
        """

        self.writer.write(b'\x04\x01\x00\x00')
        self.writer.write(key.to_bytes(4, 'big'))

    def up(self, key: int) -> None:
        """
        Releases a key.
        """

        self.writer.write(b'\x04\x00\x00\x00')
        self.writer.write(key.to_bytes(4, 'big'))

    def click(self, button):
        """
        Clicks a button down and up.
        """

        self.down(button)
        self.up(button)

    @contextmanager
    def hold(self, button):
        """
        Context manager that holds a button down, and releases it on exit.
        """

        self.down(button)
        try:
            yield
        finally:
            self.up(button)
