from asyncio import StreamWriter
from dataclasses import dataclass, field

from asyncvnc.keys import keys


@dataclass
class Keyboard:
    """
    The virtual keyboard.
    """

    writer: StreamWriter = field(repr=False)

    def update(self, key: str, down: bool) -> None:
        """
        Sends a keyboard update to the server.
        """

        self.writer.write(
            b'\x04' + down.to_bytes(1, 'big') +
            b'\x00\x00' + keys[key].to_bytes(4, 'big'))
