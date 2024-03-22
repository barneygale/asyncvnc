from asyncvnc import Video
import pytest


@pytest.fixture
def video():
    return Video(
        reader=None,
        writer=None,
        decompress=None,
        name='DESKTOP',
        width=100,
        height=200,
        mode='RGBA')


def test_getrect(video):
    assert video.get_rect() == (0,0,100,200)
    assert video.get_rect(0,0) == (0,0,100,200)
    assert video.get_rect(0,0,123,224) == (0,0,100,200)
    assert video.get_rect(-11,-12) == (0,0,100,200)
    assert video.get_rect(-11,-12,123,224) == (0,0,100,200)
    assert video.get_rect(11,12) == (11,12,89,188)
    assert video.get_rect(11,12,123,224) == (11,12,89,188)
    assert video.get_rect(11,12,23,24) == (11,12,23,24)


