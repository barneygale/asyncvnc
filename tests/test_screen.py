from asyncvnc import Screen


def test_slices():
    assert Screen(0, 0, 1, 1).slices == (slice(0, 1), slice(0, 1))
    assert Screen(1, 2, 3, 4).slices == (slice(2, 6), slice(1, 4))
    assert Screen(4, 3, 2, 1).slices == (slice(3, 4), slice(4, 6))


def test_score():
    screens = [
        Screen(0, 0, 1600, 800),
        Screen(0, 0, 1600, 900),
        Screen(0, 0, 1600, 1000),
        Screen(0, 0, 1600, 1100),
        Screen(0, 0, 1600, 1200),
        Screen(0, 0, 1600, 1300),
        Screen(0, 0, 1600, 1400),
        Screen(0, 0, 1600, 1500),
        Screen(0, 0, 1600, 1600),
    ]
    screens.sort(key=lambda screen: screen.score)
    assert screens == [
        # Irregular resolutions
        Screen(0, 0, 1600, 800),   # 1280000 pixels
        Screen(0, 0, 1600, 1100),  # 1760000 pixels
        Screen(0, 0, 1600, 1300),  # 2080000 pixels
        Screen(0, 0, 1600, 1400),  # 2240000 pixels
        Screen(0, 0, 1600, 1500),  # 2400000 pixels
        Screen(0, 0, 1600, 1600),  # 2560000 pixels

        # Regular resolutions
        Screen(0, 0, 1600, 900),   # 1440000 pixels at 16:9
        Screen(0, 0, 1600, 1000),  # 1600000 pixels at 16:10
        Screen(0, 0, 1600, 1200),  # 1920000 pixels at 4:3
    ]
