import asyncio
import platform
import signal
import subprocess
import sys
import time

import asyncvnc
import pytest


pytest_plugins = ['pytester']


# Sending signal.SIGINT on subprocess fails on windows. Use CTRL_* alternatives
if platform.system() == 'Windows':
    _KILL_SIGNAL = signal.CTRL_BREAK_EVENT
    _INT_SIGNAL = signal.CTRL_C_EVENT
    _PROC_SPAWN_WAIT = 2
else:
    _KILL_SIGNAL = signal.SIGKILL
    _INT_SIGNAL = signal.SIGINT
    _PROC_SPAWN_WAIT = 0.6 if sys.version_info < (3, 7) else 0.4


def sig_prog(proc, sig):
    '''
    Kill the process with ``sig``.

    '''
    proc.send_signal(sig)
    time.sleep(0.1)

    if not proc.poll():
        proc.send_signal(_KILL_SIGNAL)

    ret = proc.wait()
    assert ret


# TODO: parametrization with a passwd for
# https://github.com/barneygale/asyncvnc/issues/1
@pytest.fixture(
    params=[None, 'doggy'],
    ids=lambda param: f'password={param}',
)
def x11vnc(
    request,
    testdir,
):
    '''
    Run a ``x11vnc`` server as subproc.

    '''
    port = 5900
    pw = request.param
    cmdargs = [
        'x11vnc',
        '-display :0',
        '-noipv6',
        '-forever',
        '-noxdamage',
        '-ncache_cr',
        f'-rfbport {port}',
    ]

    if pw:
        cmdargs.append(f'-passwd {pw}')

    # TODO: x11 doesn't run on windows right so we don't need this?
    # i guess it depends on whether we want a test for an equivalent
    # server on windows? no clue what that project would be..
    spkwargs = {}
    if platform.system() == 'Windows':
        # without this, tests can hang on windows forever..
        spkwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = testdir.popen(
        cmdargs,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **spkwargs,
    )
    assert not proc.returncode
    time.sleep(_PROC_SPAWN_WAIT)
    yield proc, port, pw
    sig_prog(proc, _INT_SIGNAL)


@pytest.mark.parametrize(
    'force_vid', [None, 'rgba'],
    ids=lambda fv: f'force_vid={fv}',
)
def test_basic_connection_maybe_auth(
    x11vnc,
    force_vid,
):
    proc, port, pw = x11vnc

    async def run_client():
        async with asyncvnc.connect(
            'localhost',
            port=port,
            force_video_mode=force_vid,
            # TODO: show this is broken
            password=pw,

        ) as client:
            print(client)

    asyncio.run(run_client())
