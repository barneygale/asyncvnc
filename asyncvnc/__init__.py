from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass, field
from enum import Enum
from os import urandom

from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.hashes import Hash, MD5

from asyncvnc.clipboard import Clipboard
from asyncvnc.keyboard import Keyboard
from asyncvnc.mouse import Mouse
from asyncvnc.video import Video, VideoMode, VideoEncoding
from asyncvnc.utils import read_int, read_text


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
    for security_type in (30, 0, 1):
        if security_type in security_types:
            writer.write(security_type.to_bytes(1, 'big'))
            break
    else:
        raise ValueError(f'unsupported security types: {security_types}')

    # Apple authentication
    if security_type == 30:
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
    if security_type == 1:
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
