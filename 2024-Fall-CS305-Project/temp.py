import asyncio
import asyncio
import socket
import threading


from util import *
LOG_INTERVAL = 5  # Log interval in seconds



class ConferenceServer:
    def __init__(self, conference_id):
        self.conference_id = conference_id
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']
        self.clients_info = {}
        self.client_conns = []
        self.running = False
        self.mode = 'Client-Server'

    async def handle_data(self, reader, writer, data_type):
        try:
            while self.running:
                data = await reader.read(1024)
                if not data:
                    break
                # Forward to all clients except sender
                for conn in self.client_conns:
                    if conn != writer:
                        conn.write(data)
                        await conn.drain()
        except Exception as e:
            print(f"Error in handle_data: {e}")
        finally:
            writer.close()

    async def handle_client(self, reader, writer):
        try:
            self.client_conns.append(writer)
            while self.running:
                message = await reader.read(1024)
                if not message:
                    break
                # Process client message (e.g., commands, chat, etc.)
                print(f"Received message: {message.decode()}")
        except Exception as e:
            print(f"Error in handle_client: {e}")
        finally:
            self.client_conns.remove(writer)
            writer.close()

    async def log(self):
        while self.running:
            print(f"[Conference {self.conference_id}] Running with {len(self.client_conns)} clients")
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        self.running = False
        for conn in self.client_conns:
            conn.close()
        self.client_conns.clear()

    def start(self):
        self.running = True
        asyncio.create_task(self.log())


class MainServer:
    def __init__(self, server_ip, main_port):
        self.server_ip = server_ip
        self.server_port = main_port
        self.conference_servers = {}

    async def handle_create_conference(self, writer):
        conference_id = len(self.conference_servers) + 1
        server = ConferenceServer(conference_id)
        self.conference_servers[conference_id] = server
        server.start()
        writer.write(f"Conference {conference_id} created".encode())
        await writer.drain()

    async def handle_join_conference(self, writer, conference_id):
        if conference_id in self.conference_servers:
            writer.write(f"Joining Conference {conference_id}".encode())
        else:
            writer.write("Conference not found".encode())
        await writer.drain()

    async def request_handler(self, reader, writer):
        try:
            request = await reader.read(1024)
            if request:
                command = request.decode().strip()
                if command == "CREATE":
                    await self.handle_create_conference(writer)
                elif command.startswith("JOIN"):
                    conference_id = int(command.split(" ")[1])
                    await self.handle_join_conference(writer, conference_id)
                else:
                    writer.write("Unknown command".encode())
                    await writer.drain()
        except Exception as e:
            print(f"Error in request_handler: {e}")
        finally:
            writer.close()

    def start(self):
        asyncio.run(self.run_server())

    async def run_server(self):
        server = await asyncio.start_server(self.request_handler, self.server_ip, self.server_port)
        print(f"Main server running on {self.server_ip}:{self.server_port}")
        async with server:
            await server.serve_forever()


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()