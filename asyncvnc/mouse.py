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

    #: Mask of pressed buttons
    buttons: MouseButton = MouseButton.NONE

    #: Horizontal position
    x: int = 0

    #: Vertical position
    y: int = 0

    def write(self):
        """
        Sends a mouse update to the server.
        """

        self.writer.write(b'\x05')
        self.writer.write(self.buttons.value.to_bytes(1, 'big'))
        self.writer.write(self.x.to_bytes(2, 'big'))
        self.writer.write(self.y.to_bytes(2, 'big'))

    def down(self, button: MouseButton):
        """
        Presses a mouse button.
        """

        self.buttons |= button
        self.write()

    def up(self, button: MouseButton):
        """
        Releases a mouse button.
        """

        self.buttons &= ~button
        self.write()

    def move(self, x, y):
        """
        Moves the mouse pointer.
        """

        self.x = x
        self.x = y
        self.write()
