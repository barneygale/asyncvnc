from io import BytesIO
from asyncvnc import Video
import numpy as np
import pytest


@pytest.fixture
def video():
    return Video(
        reader=None,
        writer=BytesIO(),
        decompress=lambda data: data,
        name='DESKTOP',
        width=11,
        height=22,
        mode='RGBA')


def test_refresh(video):
    video.refresh()
    assert video.writer.getvalue() == b'\x03\x00\x00\x00\x00\x00\x00\x0b\x00\x16'


def test_refresh_incremental(video):
    video.data = np.zeros((22, 11, 4), 'B')
    video.refresh()
    assert video.writer.getvalue() == b'\x03\x01\x00\x00\x00\x00\x00\x0b\x00\x16'


# TODO: as_rgba()
# TODO: detect_screens()
