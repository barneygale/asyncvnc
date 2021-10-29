from asyncio import StreamWriter
from dataclasses import dataclass, field


@dataclass
class Clipboard:
    """
    Shared clipboard.
    """

    writer: StreamWriter = field(repr=False)

    #: The clipboard text.
    text: str = ''

    def update(self, text: str) -> None:
        """
        Sends clipboard text to the server.
        """

        data = text.encode('latin-1')
        self.writer.write(b'\x06\x00')
        self.writer.write(len(data).to_bytes(4, 'big'))
        self.writer.write(data)
