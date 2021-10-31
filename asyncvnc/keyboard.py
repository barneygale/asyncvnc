from asyncio import StreamWriter
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass, field

from asyncvnc.keys import keys


@dataclass
class Keyboard:
    """
    The virtual keyboard.
    """

    writer: StreamWriter = field(repr=False)

    @contextmanager
    def _hold(self, key: str):
        data = keys[key].to_bytes(4, 'big')
        self.writer.write(b'\x04\x01\x00\x00' + data)
        try:
            yield
        finally:
            self.writer.write(b'\x04\x00\x00\x00' + data)

    @contextmanager
    def hold(self, *keys: str):
        with ExitStack() as stack:
            for key in keys:
                stack.enter_context(self._hold(key))
            yield

    def press(self, *keys: str):
        with self.hold(*keys):
            pass

    def write(self, text: str):
        for key in text:
            with self.hold(key):
                pass
