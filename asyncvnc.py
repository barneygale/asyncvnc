from asyncio import StreamReader, StreamWriter
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, Flag
from os import urandom
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hashes import Hash, MD5

from numpy import ndarray, zeros, dstack


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

    MAC = 30
    NONE = 0
    VNC = 1


class UpdateType(Enum):
    """
    Update from server to client.
    """

    VIDEO = 0
    CLIPBOARD = 2
    BELL = 3


class MouseButton(Flag):
    """
    Mouse button state.
    """

    NONE = 0
    LEFT = 1
    MIDDLE = 2
    RIGHT = 4
    SCROLL_UP = 8
    SCROLL_DOWN = 16


class VideoEncoding(Enum):
    """
    Video encoding.
    """

    RAW = 0


class VideoMode(Enum):
    """
    Video mode (colour channel order)
    """

    BGRA = b'\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x10\x08\x00'
    RGBA = b'\x20\x18\x00\x01\x00\xff\x00\xff\x00\xff\x00\x08\x10'
    ARGB = b'\x20\x18\x01\x01\x00\xff\x00\xff\x00\xff\x10\x08\x00'
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
    data: Optional[ndarray] = None

    def as_rgba(self) -> ndarray:
        """
        Returns the video buffer as a 3D RGBA array.
        """

        if self.data is None:
            return zeros((self.height, self.width, 4), 'B')
        if self.mode is VideoMode.RGBA:
            return self.data
        if self.mode is VideoMode.ABGR:
            return self.data[:, :, ::-1]
        return dstack((
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
            self.data = zeros((self.height, self.width, 4), 'B')
        self.data[y:y + height, x:x + width] = ndarray((height, width, 4), 'B', data)
        self.data[y:y + height, x:x + width, self.mode.name.index('A')] = 255


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
