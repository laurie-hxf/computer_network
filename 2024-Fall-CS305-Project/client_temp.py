import asyncio
import socket
import threading


from util import *

class ConferenceClient:
    def __init__(self):
        self.is_working = True
        self.server_addr = ('127.0.0.1', 12345)  # Default server address
        self.on_meeting = False
        self.conns = []  # Maintain multiple connections
        self.support_data_types = ['screen', 'camera', 'audio']
        self.share_data = {data_type: False for data_type in self.support_data_types}
        self.conference_info = None
        self.recv_data = {}

    async def create_conference(self):
        reader, writer = await asyncio.open_connection(*self.server_addr)
        writer.write(b"CREATE\n")
        await writer.drain()
        response = await reader.read(1024)
        print(response.decode())
        writer.close()

    async def join_conference(self, conference_id):
        reader, writer = await asyncio.open_connection(*self.server_addr)
        writer.write(f"JOIN {conference_id}\n".encode())
        await writer.drain()
        response = await reader.read(1024)
        if b"Joining" in response:
            self.conference_info = response.decode()
            self.on_meeting = True
            print(f"Joined conference {conference_id}")
        else:
            print("Failed to join the conference.")
        writer.close()

    async def quit_conference(self):
        if not self.on_meeting:
            print("Not currently in a conference.")
            return
        self.on_meeting = False
        print("Quit the conference.")
        # Implement any necessary cleanup logic.

    async def cancel_conference(self):
        if not self.on_meeting:
            print("Not currently in a conference.")
            return
        reader, writer = await asyncio.open_connection(*self.server_addr)
        writer.write(b"CANCEL\n")
        await writer.drain()
        response = await reader.read(1024)
        print(response.decode())
        self.on_meeting = False
        writer.close()

    async def keep_share(self, data_type, send_conn, capture_function, compress=None, fps_or_frequency=30):
        while self.share_data.get(data_type, False):
            data = capture_function()
            if compress:
                data = compress(data)
            send_conn.write(data)
            await send_conn.drain()
            await asyncio.sleep(1 / fps_or_frequency)

    async def keep_recv(self, recv_conn, data_type, decompress=None):
        while self.on_meeting:
            data = await recv_conn.read(1024)
            if decompress:
                data = decompress(data)
            self.recv_data[data_type] = data

    def share_switch(self, data_type):
        if data_type in self.support_data_types:
            self.share_data[data_type] = not self.share_data[data_type]
            status = "enabled" if self.share_data[data_type] else "disabled"
            print(f"Sharing {data_type} is now {status}.")
        else:
            print(f"Data type {data_type} not supported.")

    async def start_conference(self):
        if not self.conference_info:
            print("No conference info available.")
            return
        # Initialize connections based on conference_info.
        print("Starting conference...")
        # Start tasks for sharing and receiving data.

    async def close_conference(self):
        self.on_meeting = False
        for conn in self.conns:
            conn.close()
        self.conns.clear()
        print("Closed conference.")

    def start(self):
        asyncio.run(self.main_loop())

    async def main_loop(self):
        while True:
            status = 'Free' if not self.on_meeting else f'OnMeeting-{self.conference_info}'
            cmd_input = input(f'({status}) Please enter a operation (enter "?" to help): ').strip().lower()
            fields = cmd_input.split(maxsplit=1)
            if len(fields) == 1:
                if cmd_input in ('?', '？'):
                    print(HELP)
                elif cmd_input == 'create':
                    await self.create_conference()
                elif cmd_input == 'quit':
                    await self.quit_conference()
                elif cmd_input == 'cancel':
                    await self.cancel_conference()
                else:
                    print(f'[Warn]: Unrecognized command {cmd_input}')
            elif len(fields) == 2:
                if fields[0] == 'join':
                    conference_id = fields[1]
                    if conference_id.isdigit():
                        await self.join_conference(conference_id)
                    else:
                        print("[Warn]: Conference ID must be a number.")
                elif fields[0] == 'switch':
                    self.share_switch(fields[1])
                else:
                    print(f'[Warn]: Unrecognized command {cmd_input}')
            else:
                print(f'[Warn]: Unrecognized command {cmd_input}')


if __name__ == '__main__':
    client = ConferenceClient()
    client.start()