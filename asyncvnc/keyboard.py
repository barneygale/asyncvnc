from asyncio import StreamWriter
from dataclasses import dataclass, field

from asyncvnc.keys import keys


@dataclass
class Keyboard:
    """
    The virtual keyboard.
    """

    writer: StreamWriter = field(repr=False)

    def down(self, key: str) -> None:
        """
        Presses a key.
        """

        self.writer.write(b'\x04\x01\x00\x00' + keys[key].to_bytes(4, 'big'))

    def up(self, key: str) -> None:
        """
        Releases a key.
        """

        self.writer.write(b'\x04\x00\x00\x00' + keys[key].to_bytes(4, 'big'))
