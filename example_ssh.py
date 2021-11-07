import asyncio
import asyncvnc
import asyncssh


host = '192.168.1.111'
port = 5900
username = 'myusername'
password = 'mypassword'


async def main():
    async with asyncssh.connect(host, username=username, password=password) as conn:
        reader, writer = await conn.open_connection('localhost', 5900)
        client = await asyncvnc.Client.create(reader, writer, username, password)
        print(client)


asyncio.run(main())
