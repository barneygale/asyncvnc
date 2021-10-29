from asyncio import StreamWriter
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

    def update(self, x: int, y: int, buttons: MouseButton):
        """
        Sends a mouse update to the server.
        """

        self.writer.write(b'\x05')
        self.writer.write(buttons.value.to_bytes(1, 'big'))
        self.writer.write(x.to_bytes(2, 'big'))
        self.writer.write(y.to_bytes(2, 'big'))
