import asyncio
import socket
import threading

from util import *


class ConferenceServer:
    def __init__(self, conference_id,creator):
        # async server
        self.conference_id = conference_id  # conference_id for distinguish difference conference
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        #•	屏幕共享（screen）可能使用一个端口。
	    #•	摄像头视频流（camera）使用另一个端口。
	    #•	音频（audio）可能使用第三个端口。
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = None
        self.client_conns = None
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode
        self.creator = creator

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """
        # print(f"Handling data of type {data_type} for client.")
        try:
            while True:
                # 从客户端读取数据
                data = await reader.read(1024)
                if not data:
                    break  # 连接关闭时退出循环

                # 将数据转发给其他客户端
                for client_writer in self.client_conns.values():
                    if client_writer != writer:  # 不发给自己
                        client_writer.write(data)
                        await client_writer.drain()  # 确保发送完成
        except Exception as e:
            print(f"Error handling {data_type} data: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """
        addr = writer.get_extra_info('peername')
        print(f"Client connected: {addr}")

        # 注册客户端
        client_id = str(addr)  # 你可以自定义更复杂的客户端标识符
        self.client_conns[client_id] = writer

        try:
            while True:
                # 接收客户端请求
                data = await reader.read(1024)
                if not data:
                    break

                message = data.decode().strip()
                print(f"Received message from {addr}: {message}")

                # 简单的控制协议处理
                if message == "EXIT":
                    print(f"Client {addr} requested to exit.")
                    break
                elif message.startswith("DATA_TYPE"):
                    _, data_type = message.split()
                    await self.handle_data(reader, writer, data_type)
                else:
                    print(f"Unknown request from {addr}: {message}")
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            # 移除客户端连接
            del self.client_conns[client_id]
            writer.close()
            await writer.wait_closed()
            print(f"Client disconnected: {addr}")

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """
        print(f"Cancelling conference {self.conference_id}...")
        for client_id, writer in self.client_conns.items():
            try:
                writer.write("CONFERENCE_CANCELLED".encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                print(f"Error disconnecting client {client_id}: {e}")
        self.client_conns.clear()
        print("All clients disconnected. Conference cancelled.")


    def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''

        async def server_task():
            server = await asyncio.start_server(
                self.handle_client,  # 每个客户端的连接交由 handle_client 处理
                '0.0.0.0',  # 监听所有 IP
                self.conf_serve_ports
            )
            print(f"ConferenceServer {self.conference_id} started on port {self.conf_serve_ports}.")

            async with server:
                # 启动日志记录任务
                log_task = asyncio.create_task(self.log())

                # 保持服务器运行直到取消
                await server.serve_forever()

        asyncio.run(server_task())


class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceManager


    def handle_creat_conference(self,conn):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        # conn.sendall("Enter conference name: ".encode())
        # conference_name = conn.recv(1024).decode().strip()

        conference_id = len(self.conference_servers) + 1
        conference_server = ConferenceServer(conference_id,conn)
        self.conference_servers[conference_id] = conference_server

        conn.sendall(f"Conference created successfully! ID: {conference_id}\n".encode())


    def handle_join_conference(self, conn):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """
        # 判断当前是否有正在进行的会议
        conference_ids = list(self.conference_servers.keys())
        if len(conference_ids) == 0:
            conn.sendall("The conference server is empty.\n".encode())
            return
        else:
            conn.sendall(" ".encode())
        # conn.sendall("Enter conference ID: ".encode())
        conference_id = conn.recv(1024).decode().strip()
        if  self.conference_servers.get(int(conference_id)) is None:
            conn.sendall("Conference not found.\n".encode())
            return
        else:
            # conn.sendall(" ".encode())
            conference_server = self.conference_servers[int(conference_id)]
            conn.sendall(f"Joining conference {conference_id}...\n".encode())
            threading.Thread(target=conference_server.handle_client, args=(conn, conn.getpeername())).start()

    def ls_conference(self, conn):
        # 传会议列表给用户
        conference_ids = list(self.conference_servers.keys())
        if len(conference_ids) == 0:
            conn.sendall("The conference server is empty.\n".encode())
            return
        conference_ids_str = "\n".join(map(str, conference_ids))
        conn.sendall(conference_ids_str.encode())

    def handle_quit_conference(self,conn):
        """
        quit conference (in-meeting request & or no need to request)
        """
        for conference_id, conference in self.conference_servers.items():
            with conference.lock:
                for client, client_addr in conference.clients:
                    if client == conn:
                        conference.quit_client(client, client_addr)
                        return

        conn.sendall("You are not in any conference.\n".encode())


    def handle_cancel_conference(self,conn):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        conn.sendall("Enter conference ID to cancel: ".encode())
        conference_id = conn.recv(1024).decode().strip()
        if conference_id not in self.conference_servers:
            conn.sendall("Conference not found.\n".encode())
            return

        conference_server = self.conference_servers.pop(conference_id)
        conference_server.cancel_conference()
        conn.sendall(f"Conference {conference_id} has been cancelled.\n".encode())


    def request_handler(self, conn, addr):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        # conn.sendall("Welcome to the Video Conference Server!\n".encode())
        try:
            while True:
                choice = conn.recv(1024).decode().strip()
                if not choice:
                    # 如果客户端关闭连接或发送空消息
                    break
                if choice == "create":
                    self.handle_creat_conference(conn)
                elif choice == "join":
                    self.handle_join_conference(conn)
                elif choice == "ls":
                    self.ls_conference(conn)
                else:
                    conn.sendall("Invalid choice.\n".encode())
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            conn.sendall(f"Error: {e}\n".encode())  # 可选，向客户端发送错误信息
        finally:
            print(f"Closing connection with {addr}")
            conn.close()  # 关闭连接

    def start(self):
        """
        start MainServer
        """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.server_ip, self.server_port))
        self.server_socket.listen(5)
        print(f"Server started at {self.server_ip}:{self.server_port}")

        try:
            while True:
                conn, addr = self.server_socket.accept()
                print(f"New connection from {addr}")
                self.request_handler(conn, addr)
                # threading.Thread(target=self.request_handler, args=(conn, addr)).start()
        finally:
            self.server_socket.close()



if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()
