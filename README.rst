AsyncVNC: Asynchronous VNC for Python
=====================================

.. image:: https://img.shields.io/badge/source-github-orange
    :target: https://github.com/barneygale/asyncvnc

.. image:: https://readthedocs.org/projects/asyncvnc/badge/?version=latest&style=flat-square
    :target: https://asyncvnc.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/pypi/v/asyncvnc?style=flat-square
    :target: https://pypi.org/project/asyncvnc

.. image:: https://github.com/barneygale/asyncvnc/actions/workflows/ci.yml/badge.svg
    :target: https://github.com/barneygale/asyncvnc/actions



AsyncVNC is a Python package which provides an asynchronous client implementation of the VNC (RFB) protocol on top of
the asyncio framework.

.. code-block::

    import asyncio, asyncvnc

    async def run_client():
        with asyncvnc.connect('localhost', 5900, 'username', 'password') as client:
            client.keyboard.write('hello world!')

    asyncio.run(run_client())


Features
--------

- Full support for keyboard, mouse, video and clipboard updates.

  * The frame buffer can be exported as an RGBA numpy array.
  * Keyboard keys are specified by name or character.

- Compatibility with traditional VNC servers (RealVNC, TightVNC, TigerVNC, etc).

  * Including unauthenticated connections.
  * Including password authentication with Triple DES.

- Compatibility with the built-in macOS Remote Desktop server.

  * Including username/password authentication with 2048-bit RSA keys and 128-bit AES.
  * Connects to the desktop, not the login screen.

- Detection of multi-head frame buffer data using a novel algorithm.
- Support for tunneling VNC over SSH with AsyncSSH.
- Support for image data compression with zlib.


Installation
------------

This package requires Python 3.7+.

Install AsyncVNC by running::

    pip install asyncvnc


Connecting to a server
----------------------

This snippet connects to a local unauthenticated VNC server, prints information, and disconnects::

    import asyncio, asyncvnc

    async def run_client():
        async with asyncvnc.connect('localhost') as client:
            print(client)

    asyncio.run(run_client())

To log in to a macOS server, supply *username* and *password* arguments::

    async with asyncvnc.connect('localhost', username='user123', password='h4x0r'):
        ...

For traditional authenticated VNC servers, the *password* argument is required but not *username*.

.. warning::

    Traditional VNC authentication is woefully insecure. For best results, configure your VNC server to listen only on
    ``127.0.0.1``. If you need external access, use an SSH tunnel.


To tunnel VNC over SSH, use the AsyncSSH package (after which this package is modelled)::

    import asyncio, asyncssh, asyncvnc

    async def run_client():
        async with asyncssh.connect('myserver') as conn:
            async with asyncvnc.connect('localhost', opener=conn.open_connection) as client:
                print(client)

    asyncio.run(run_client())


Sending events
--------------

Keyboard and mouse objects provide context managers for holding down keys and buttons::

    with client.keyboard.hold('Ctrl'):
        ...

    with client.mouse.hold():
        ...

The keyboard has methods for pressing keys and writing text::

    client.keyboard.press('Ctrl', 'c')  # keys are stacked
    client.keyboard.write('hi there!')  # keys are queued

The mouse has methods for moving the cursor and clicking::

    client.mouse.move(100, 200)
    client.mouse.click()
    client.mouse.right_click()
    client.mouse.scroll_up()


Taking a screenshot
-------------------

To retrieve an image from the VNC server and save it as a PNG file::

    import asyncio, asyncvnc
    from PIL import Image

    async def read_updates(client):
        while True:
            await client.read()

    async def run_client():
        async with asyncvnc.connect('localhost') as client:

            # Request a video update
            client.video.refresh()

            # Handle packets for a few seconds
            try:
                await asyncio.wait_for(read_updates(client), 3.0)
            except asyncio.TimeoutError:
                pass

            # Retrieve pixels as a 3D numpy array
            pixels = client.video.as_rgba()

            # Save as PNG using PIL/pillow
            image = Image.fromarray(pixels)
            image.save('screenshot.png')

    asyncio.run(run_client())


The macOS VNC server composites attached monitors/screens into a single frame buffer. It does not send updates for
unoccupied regions; we can use this information to detect screens::

    pixels = client.video.as_rgba()
    for screen in client.video.detect_screens():
        screen_pixels = pixels[screen.slices]

