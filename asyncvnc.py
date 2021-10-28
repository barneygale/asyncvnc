from asyncio import StreamReader, StreamWriter
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, Flag
from fractions import Fraction
from itertools import product
from os import urandom
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hashes import Hash, MD5

import numpy as np


#: Common screen aspect ratios
screen_ratios = {Fraction(3, 2), Fraction(4, 3), Fraction(16, 10), Fraction(16, 9), Fraction(32, 9), Fraction(64, 27)}


async def read_int(reader: StreamReader, length: int) -> int:
    """
    Reads, unpacks, and returns an integer of *length* bytes.
    """

    return int.from_bytes(await reader.readexactly(length), 'big')


async def read_text(reader: StreamReader, encoding: str) -> str:
    """
    Reads, unpacks, and returns length-prefixed text.
    """

    length = await read_int(reader, 4)
    text = await reader.readexactly(length)
    return text.decode(encoding)


class SecurityType(Enum):
    """
    VNC security type.
    """

    #: macOS authentication
    MAC = 30

    #: No authentication
    NONE = 0

    #: VNC authentication
    VNC = 1


class UpdateType(Enum):
    """
    Update from server to client.
    """

    #: Video update
    VIDEO = 0

    #: Clipboard update
    CLIPBOARD = 2

    #: Bell update
    BELL = 3


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


class VideoEncoding(Enum):
    """
    Video encoding.
    """

    #: Raw encoding
    RAW = 0


class VideoMode(Enum):
    """
    Video mode (colour channel order)
    """

    #: Blue, green, red, alpha
    BGRA = b'\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x10\x08\x00'

    #: Red, green, blue, alpha
    RGBA = b'\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x00\x08\x10'

    #: Alpha, red, green, blue
    ARGB = b'\x20\x18\x01\x01\x00\xff\x00\xff\x00\xff\x10\x08\x00'

    #: Alpha, blue, green, red
    ABGR = b'\x20\x18\x01\x01\x00\xff\x00\xff\x00\xff\x00\x08\x10'

    def __repr__(self) -> str:
        return '<%s.%s>' % (self.__class__.__name__, self.name)


@dataclass
class Clipboard:
    """
    Shared clipboard.
    """

    writer: StreamWriter = field(repr=False)

    #: The clipboard text.
    text: str = ''

    def write(self) -> None:
        """
        Sends clipboard text to the server.
        """

        data = self.text.encode('latin-1')
        self.writer.write(b'\x06\x00')
        self.writer.write(len(data).to_bytes(4, 'big'))
        self.writer.write(data)


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


@dataclass
class Mouse(Keyboard):
    """
    The virtual mouse.
    """

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
        self.writer.write(self.buttons.to_bytes(1, 'big'))
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


@dataclass
class Screen:
    """
    A computer screen.
    """

    #: Horizontal position in pixels
    x: int

    #: Vertical position in pixels
    y: int

    #: Width in pixels
    width: int

    #: Height in pixels
    height: int

    @property
    def slice(self) -> tuple[slice, slice]:
        """
        Object that can be used to crop the video buffer to this screen.
        """

        return (slice(self.y, self.y + self.height), slice(self.x, self.x + self.width))

    @property
    def score(self) -> float:
        """
        A measure of our confidence that this represents a real screen. For screens with standard aspect ratios, this
        is proportional to its pixel area. For non-standard aspect ratios, the score is further multiplied by the ratio
        or its reciprocal, whichever is smaller.
        """

        value = float(self.width * self.height)
        ratios = {Fraction(self.width, self.height).limit_denominator(64),
                  Fraction(self.height, self.width).limit_denominator(64)}
        if not ratios & screen_ratios:
            value *= min(ratios)
        return value


@dataclass
class Video:
    """
    Image buffer.
    """

    writer: StreamWriter = field(repr=False)

    #: Colour channel order
    mode: VideoMode

    #: Width in pixels
    width: int

    #: Height in pixels
    height: int

    #: 3D numpy array of colour data
    data: Optional[np.ndarray] = None

    def as_rgba(self) -> np.ndarray:
        """
        Returns the video buffer as a 3D RGBA array.
        """

        if self.data is None:
            return np.zeros((self.height, self.width, 4), 'B')
        if self.mode is VideoMode.RGBA:
            return self.data
        if self.mode is VideoMode.ABGR:
            return self.data[:, :, ::-1]
        return np.dstack((
            self.data[:, :, self.mode.name.index('R')],
            self.data[:, :, self.mode.name.index('G')],
            self.data[:, :, self.mode.name.index('B')],
            self.data[:, :, self.mode.name.index('A')]))

    def write_request(self) -> None:
        """
        Sends a video buffer update request to the server.
        """

        incremental = self.data is not None
        self.writer.write(b'\x03')
        self.writer.write(incremental.to_bytes(1, 'big'))
        self.writer.write(b'\x00\x00\x00\x00')  # x, y
        self.writer.write(self.width.to_bytes(2, 'big'))
        self.writer.write(self.height.to_bytes(2, 'big'))

    def update(self, data: bytes, x: int, y: int, width: int, height: int) -> None:
        """
        Updates a portion of the video buffer.
        """

        if self.data is None:
            self.data = np.zeros((self.height, self.width, 4), 'B')
        self.data[y:y + height, x:x + width] = np.ndarray((height, width, 4), 'B', data)
        self.data[y:y + height, x:x + width, self.mode.name.index('A')] = 255

    def detect_screens(self) -> tuple[Screen]:
        """
        Detect physical screens by inspecting the alpha channel.
        """

        if self.data is None:
            return tuple()

        mask = self.data[:, :, self.mode.name.index('A')]
        mask = np.pad(mask // 255, ((1, 1), (1, 1))).astype(np.int8)
        mask_a = mask[1:, 1:]
        mask_b = mask[1:, :-1]
        mask_c = mask[:-1, 1:]
        mask_d = mask[:-1, :-1]

        screens = []
        while True:
            # Detect corners by ANDing perpendicular pairs of differences.
            corners = product(
                np.argwhere(mask_b - mask_a & mask_c - mask_a == -1),  # top left
                np.argwhere(mask_a - mask_b & mask_d - mask_b == -1),  # top right
                np.argwhere(mask_d - mask_c & mask_a - mask_c == -1),  # bottom left
                np.argwhere(mask_c - mask_d & mask_b - mask_d == -1))  # bottom right

            # Find cases where 3 corners align, forming an  'L' shape.
            candidates = set()
            for a, b, c, d in corners:
                ab = a[0] == b[0] and a[1] < b[1]  # top
                cd = c[0] == d[0] and c[1] < d[1]  # bottom
                ac = a[1] == c[1] and a[0] < c[0]  # left
                bd = b[1] == d[1] and b[0] < d[0]  # right
                ab and ac and candidates.add((a[1], a[0], b[1], c[0]))
                ab and bd and candidates.add((a[1], a[0], d[1], d[0]))
                cd and ac and candidates.add((a[1], a[0], d[1], d[0]))
                cd and bd and candidates.add((c[1], b[0], d[1], d[0]))

            # Create screen objects and sort them by their scores.
            candidates = [Screen(int(x0), int(y0), int(x1 - x0), int(y1 - y0)) for x0, y0, x1, y1 in candidates]
            candidates.sort(key=lambda screen: screen.score, reverse=True)

            # Find a single fully-opaque screen
            for screen in candidates:
                if mask_a[screen.slice].all():
                    mask_a[screen.slice] = 0
                    screens.append(screen)
                    break

            # Finish up if no screens remain
            else:
                return tuple(screens)


@dataclass
class Client:
    """
    VNC Client.
    """

    reader: StreamReader = field(repr=False)

    #: The name of the desktop.
    name: str

    #: The shared clipboard.
    clipboard: Clipboard

    #: The keyboard.
    keyboard: Keyboard

    #: The pointing device.
    mouse: Mouse

    #: The video buffer.
    video: Video

    async def read(self) -> UpdateType:
        """
        Reads and returns an update from the server.
        """

        update_type = UpdateType(await read_int(self.reader, 1))

        if update_type is UpdateType.CLIPBOARD:
            await self.reader.readexactly(3)  # padding
            self.clipboard.text = await read_text(self.reader, 'latin-1')

        if update_type is UpdateType.VIDEO:
            await self.reader.readexactly(1)  # padding
            for _ in range(await read_int(self.reader, 2)):
                x = await read_int(self.reader, 2)
                y = await read_int(self.reader, 2)
                width = await read_int(self.reader, 2)
                height = await read_int(self.reader, 2)
                encoding = VideoEncoding(await read_int(self.reader, 4))
                if encoding is VideoEncoding.RAW:
                    data = await self.reader.readexactly(height * width * 4)
                    self.video.update(data, x, y, width, height)

        return update_type


async def auth(reader: StreamReader, writer: StreamWriter, username: str = '', password: str = '') -> Client:
    """
    Authenticates with a VNC server and returns a client.
    """

    await reader.readexactly(12)
    writer.write(b'RFB 003.008\n')

    security_types = set(await reader.readexactly(await read_int(reader, 1)))
    for security_type in SecurityType:
        if security_type.value in security_types:
            writer.write(security_type.value.to_bytes(1, 'big'))
            break
    else:
        raise ValueError(f'unsupported security types: {security_types}')

    # Apple authentication
    if security_type is SecurityType.MAC:
        if not username or not password:
            raise ValueError('server requires username and password')
        g = await read_int(reader, 2)  # generator
        s = await read_int(reader, 2)  # key size
        p = await read_int(reader, s)  # prime modulus
        y = await read_int(reader, s)  # public key
        parameter_numbers = dh.DHParameterNumbers(p, g)
        server_public_numbers = dh.DHPublicNumbers(y, parameter_numbers)
        private_key = parameter_numbers.parameters().generate_private_key()
        public_numbers = private_key.public_key().public_numbers()
        aes_key = private_key.exchange(server_public_numbers.public_key())
        md5_hash = Hash(MD5())
        md5_hash.update(aes_key)
        aes_key = md5_hash.finalize()
        encryptor = Cipher(algorithms.AES(aes_key), modes.ECB()).encryptor()
        for item in (username, password):
            data = item.encode('utf8') + b'\x00'
            data = data + urandom(64 - len(data))
            writer.write(encryptor.update(data))
        writer.write(encryptor.finalize())
        writer.write(public_numbers.y.to_bytes(s, 'big'))

    # VNC authentication
    if security_type is SecurityType.VNC:
        if not password:
            raise ValueError('server requires password')
        des_key = password[:8].encode('ascii')
        des_key = des_key + b'\x00' * (8 - len(des_key))
        des_key = des_key + des_key + des_key
        encryptor = Cipher(algorithms.TripleDES(des_key), modes.ECB()).encryptor()
        challenge = await reader.readexactly(16)
        writer.write(encryptor.update(challenge) + encryptor.finalize())

    auth_result = await read_text(reader, 'utf-8')
    if auth_result:
        raise PermissionError(auth_result)

    writer.write(b'\x01')
    width = await read_int(reader, 2)
    height = await read_int(reader, 2)
    video_mode = await reader.readexactly(13)
    await reader.readexactly(3)  # padding
    name = await read_text(reader, 'utf-8')

    writer.write(b'\x02\x00')
    writer.write(len(VideoEncoding).to_bytes(2, 'big'))
    for encoding in VideoEncoding:
        writer.write(encoding.value.to_bytes(4, 'big'))

    return Client(
        reader=reader,
        name=name,
        clipboard=Clipboard(writer),
        keyboard=Keyboard(writer),
        mouse=Mouse(writer),
        video=Video(writer, VideoMode(video_mode), width, height))
