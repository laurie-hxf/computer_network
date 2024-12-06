import asyncio
from util import *


class ConferenceServer:
    def __init__(self, id, creator):
        # async server
        self.conference_id = id  # conference_id for distinguish difference conference
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = None
        self.client_conns = []
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode
        self.running=True
        self.creator = creator

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """
        print("why")
        self.client_conns.append(writer)
        # 一直监听客户端数据
        try:
            while self.running:
                data = await reader.read(1000)  # 获取数据流
                if not data:
                    break
                # 处理数据流
                message = data.decode().strip()
                if message.startswith("quit"):
                    if writer is self.creator:
                        self.running = False
                        print("quit")
                        writer.write("quit successfully".encode())
                        await writer.drain()
                        self.client_conns.remove(writer)

                    else:
                        writer.write("quit successfully".encode())
                        await writer.drain()
                        self.client_conns.remove(writer)


                elif message.startswith("cancel"):
                    print("cancel")
                    if writer is self.creator:
                        self.running = False
                    else:
                        writer.write("you have no quality to cancel this session".encode())

                else:
                    # 处理未知命令
                    writer.write("invalid command".encode())

                # await self.handle_data(reader, writer, 'screen')  # 假设处理的是屏幕数据
            # 客户端断开连接
            await self.cancel_conference()
        except Exception as e:
            print(e)
        # self.client_conns.remove(writer)
        # writer.close()

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """
        for c in self.client_conns:
            self.client_conns.remove(c)
            # c.close()

    async def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''
        self.running = True
        # await self.handle_client(self.creator, self.creator)
        server_temp = await asyncio.start_server(self.handle_client, SERVER_IP, 0)
        port = server_temp.sockets[0].getsockname()[1]
        self.conf_serve_ports=port

        # loop = asyncio.get_event_loop()
        # coro = asyncio.start_server(self.handle_client, SERVER_IP, 0, loop=loop)
        # self.running = True
        # loop.run_forever()

        # 启动日志输出任务（并行执行）
        # asyncio.create_task(self.log())

        await server_temp.serve_forever()


class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None

        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceManager

    async def handle_create_conference(self,reader, writer):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        conference_id = len(self.conference_servers) + 1
        conference_server = ConferenceServer(conference_id,writer)
        self.conference_servers[conference_id] = conference_server
        # await conference_server.start()
        asyncio.create_task(conference_server.start())
        writer.write(f"Conference created successfully! ID: {conference_id}\n".encode())
        await writer.drain()
        await conference_server.handle_client(reader, writer)

    async def handle_join_conference(self, reader, writer,conference_id):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """
        if int(conference_id) in self.conference_servers:
            server = self.conference_servers[int(conference_id)]
            writer.write(f"Joined conference {conference_id}".encode())
            await writer.drain()
            # 将客户端连接到会议服务器
            await server.handle_client(reader, writer)
        else:
            writer.write(f"Conference {conference_id} does not exist".encode())
            await writer.drain()

    async def ls_conference(self, writer):
        # 传会议列表给用户
        conference_ids = list(self.conference_servers.keys())
        if len(conference_ids) == 0:
            writer.write("The conference server is empty.\n".encode())
            return
        conference_ids_str = "\n".join(map(str, conference_ids))
        writer.write(conference_ids_str.encode())
        await writer.drain()

    def handle_quit_conference(self):
        """
        quit conference (in-meeting request & or no need to request)
        """
        pass

    def handle_cancel_conference(self):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        pass

    async def request_handler(self, reader, writer):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        while True:
            data = await reader.read(100)
            message = data.decode()

            if message.startswith("create"):
                await self.handle_create_conference(reader,writer)
                # break


            elif message.startswith("join"):
                # 使用 split() 方法分割字符串
                parts = message.split()  # 默认按空格分割
                if len(parts) > 1:
                    # 获取第二部分，即 id
                    conference_id = parts[1]
                    await self.handle_join_conference(reader, writer,conference_id)
                    print(f"The conference ID is: {conference_id}")
                else:
                    writer.write("no conference id".encode())


            elif message.startswith("ls"):
                await self.ls_conference(writer)

            else:
                writer.write("invalid command".encode())
            # 其他处理方法


    def start(self):
        """
        start MainServer
        """

        loop = asyncio.get_event_loop()
        # coro = asyncio.start_server(self.request_handler, self.server_ip, self.server_port, loop=loop)
        coro = asyncio.start_server(self.request_handler, self.server_ip, self.server_port)
        self.main_server = loop.run_until_complete(coro)
        print(f"Main server started on {self.server_ip}:{self.server_port}")
        loop.run_forever()


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()