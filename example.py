import asyncio
import asyncvnc
from PIL import Image


host = '192.168.1.111'
port = 5900
username = 'myusername'
password = 'mypassword'
filename = 'screenshot.png'


async def read_task(client):
    while True:
        try:
            update = await client.read()
            print('received', update)
        except asyncio.CancelledError:
            break


async def main():
    print('connecting')
    reader, writer = await asyncio.open_connection(host, port)

    print('authenticating')
    client = await asyncvnc.auth(reader, writer, username, password)

    print('requesting image')
    client.video.write_request()

    print('handling packets')
    try:
        await asyncio.wait_for(read_task(client), 5.0)
    except asyncio.TimeoutError:
        pass

    print('loading image')
    image = Image.fromarray(client.video.as_rgba())

    print('saving image')
    image.save(filename)

    print('disconnecting')
    writer.close()
    await writer.wait_closed()


asyncio.run(main())
