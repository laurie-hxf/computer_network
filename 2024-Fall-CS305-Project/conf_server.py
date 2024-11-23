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
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = None
        self.client_conns = None
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode
        self.creator = creator

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """
        self.active = False
        with self.lock:
            for client, addr in self.clients:
                try:
                    client.sendall("The conference has been cancelled by the host.\n".encode())
                    client.close()
                except:
                    pass
            self.clients.clear()

    def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''


class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceManager
        self.conference_passwords = {} ## {conference_id: password}

    def handle_creat_conference(self,conn):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        # conn.sendall("Enter conference name: ".encode())
        # conference_name = conn.recv(1024).decode().strip()
        conn.sendall("Set a password for the conference: ".encode())
        password = conn.recv(1024).decode().strip()

        conference_id = f"conf_{len(self.conference_servers) + 1}"
        conference_server = ConferenceServer(conference_id,conn)
        self.conference_servers[conference_id] = conference_server
        self.conference_passwords[conference_id] = password

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

        # 传会议列表给用户
        conference_ids_str = "\n".join(conference_ids)+"\nEnter conference ID: "
        conn.sendall(conference_ids_str.encode())
        # conn.sendall("Enter conference ID: ".encode())
        conference_id = conn.recv(1024).decode().strip()
        if conference_id not in self.conference_servers:
            conn.sendall("Conference not found.\n".encode())
            return

        # 要求用户提供会议的密码
        conn.sendall("Enter password: ".encode())
        password = conn.recv(1024).decode().strip()
        conference_server = self.conference_servers[conference_id]

        # 判断密码是否正确
        if conference_server.password != password:
            conn.sendall("Incorrect password.\n".encode())
            return

        conn.sendall(f"Joining conference {conference_id}...\n".encode())
        threading.Thread(target=conference_server.handle_client, args=(conn, conn.getpeername())).start()

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
        pass

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
        pass

    async def request_handler(self, conn, addr):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        while True:
            conn.sendall("Welcome to the Video Conference Server!\n".encode())
            try:
                conn.sendall("1. Create Conference\n2. Join Conference\nEnter your choice: ".encode())
                choice = conn.recv(1024).decode().strip()

                if choice == "1":
                    self.handle_creat_conference(conn)
                elif choice == "2":
                    self.handle_join_conference(conn)
                else:
                    conn.sendall("Invalid choice. Disconnecting.\n".encode())
            except Exception as e:
                print(f"Error handling client {addr}: {e}")
            finally:
                conn.close()


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
                threading.Thread(target=self.request_handler, args=(conn, addr)).start()
        finally:
            self.server_socket.close()
        pass


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()
