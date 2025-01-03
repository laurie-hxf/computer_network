import socket
import asyncio
import threading

from util import *


class ConferenceClient:
    def __init__(self,):
        # sync client
        self.is_working = True
        self.server_addr = (SERVER_IP,MAIN_SERVER_PORT)  # server addr
        self.on_meeting = False  # status
        self.conns = None  # you may need to maintain multiple conns for a single conference
        self.support_data_types = []  # for some types of data
        self.share_data = {}
        self.conference_id=None

        self.conference_info = None  # you may need to save and update some conference_info regularly

        self.recv_data = None  # you may need to save received streamd data from other clients in conference

    def create_conference(self):
        """
        create a conference: send create-conference request to server and obtain necessary data to
        """
        if self.on_meeting is False:
            try:
                self.conns.sendall("create".encode())
                confirmation = self.conns.recv(1024).decode()
                print(confirmation)
                config_id=confirmation.split(":")[1]
                self.conference_info = config_id
                self.on_meeting = True
                self.conference_id = int(config_id)
                self.start_conference(self.conns)

            except Exception as e:
                print(f"[Error]: Failed to create conference: {e}")
        else:
            print("[Error]: you have already join in a conference")

    def ls_conference(self):
        if self.on_meeting is False:
            try:
                self.conns.sendall("ls".encode())
                response = self.conns.recv(1024).decode()
                print(response)
            except Exception as e:
                print(f"[Error]: Failed to create conference: {e}")
        else:
            print("[Error]: you have already join in a conference, can't ls it")
    def join_conference(self, conference_id):
        """
        join a conference: send join-conference request with given conference_id, and obtain necessary data to
        """
        if self.on_meeting is False:
            try:
                self.conns.sendall(f"join {conference_id}".encode())

                confirmation = self.conns.recv(1024).decode()
                print(confirmation)

                if "Joined conference" in confirmation:
                    self.on_meeting = True
                    self.conference_id = conference_id

                    # Start receiving data in a separate thread
                    # threading.Thread(target=self.keep_recv, args=(self.conns,)).start()
            except Exception as e:
                print(f"[Error]: Failed to join conference: {e}")
        else:
             print("[Error]: you have already join in a conference")

    def quit_conference(self):
        """
        quit your on-going conference
        """
        if self.on_meeting is True:
            try:
                self.conns.sendall("quit".encode())
                confirmation = self.conns.recv(1024).decode()
                print(confirmation)

                if "successfully" in confirmation:
                    self.on_meeting = False
                    self.conference_id = None
                elif "cancel conference" in confirmation:
                    print("[Info]: Conference has been canceled by the server.")
                    self.on_meeting = False
                    self.conference_id = None

            except Exception as e:
                print(f"[Error]: Failed to quit conference: {e}")

        else:
            print("[Error]: you are not on meeting")

    def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        if self.on_meeting is True:
            try:
                self.conns.sendall("cancel".encode())
                confirmation = self.conns.recv(1024).decode()
                print(confirmation)

                if "successfully" in confirmation:
                    self.on_meeting = False
                    self.conference_id = None
                elif "cancel conference" in confirmation:
                    print("[Info]: Conference has been canceled by the server.")
                    self.on_meeting = False
                    self.conference_id = None

            except Exception as e:
                print(f"[Error]: Failed to quit conference: {e}")

        else:
            print("[Error]: you are not on meeting")


    def keep_share(self, data_type, send_conn, capture_function, compress=None, fps_or_frequency=30):
        '''
        running task: keep sharing (capture and send) certain type of data from server or clients (P2P)
        you can create different functions for sharing various kinds of data
        '''
        import time
        interval = 1 / fps_or_frequency  # 每次捕获的时间间隔

        while True:
            try:
                # 捕获数据
                data = capture_function()
                # 压缩数据（如果需要）
                if compress:
                    data = compress(data)
                # 发送数据
                send_conn.send(data)
                # 控制频率
                time.sleep(interval)

            except Exception as e:
                print(f"Error in keep_share({data_type}): {e}")
                break

    def share_switch(self, data_type,send_conn):
        '''
        switch for sharing certain type of data (screen, camera, audio, etc.)
        '''
        # if enable:
        # def keep_share(self, data_type, send_conn, capture_function, compress=None, fps_or_frequency=30):
        # 创建一个线程来共享数据
        global thread
        if data_type == "screen":
            thread = threading.Thread(target=self.keep_share, args=('screen', self.conns,capture_screen(),))
        elif data_type == "camera":
            thread = threading.Thread(target=self.keep_share, args=('camera', send_conn ,capture_camera(),compress_image()))
        elif data_type == "audio":
            thread = threading.Thread(target=self.keep_share, args=('audio', send_conn ,capture_voice()))

        thread.daemon = True
        thread.start()
        # self.active_shares[data_type] = thread
        # else:
        #     if data_type in self.active_shares:
        #         # 停止共享
        #         self.active_shares[data_type].stop()
        #         del self.active_shares[data_type]

    def keep_recv(self, recv_conn, data_type, decompress=None):
        '''
        running task: keep receiving certain type of data (save or output)
        you can create other functions for receiving various kinds of data
        '''
        while True:
            try:
                # 接收数据
                data = recv_conn.recv()

                # 解压数据（如果需要）
                if decompress:
                    data = decompress(data)

                # 存储或处理数据
                self.data_buffers[data_type].append(data)

            except Exception as e:
                print(f"Error in keep_recv({data_type}): {e}")
                break

    def output_data(self):
        '''
        running task: output received stream data
        '''
        while True:
            try:
                # 处理屏幕图像
                if 'screen' in self.data_buffers:
                    screen_data = self.data_buffers['screen'].pop(0)
                    screen_image = Image.open(BytesIO(screen_data))
                    screen_image.show()

                # 处理摄像头图像
                if 'camera' in self.data_buffers:
                    camera_data = self.data_buffers['camera'].pop(0)
                    camera_image = Image.open(BytesIO(camera_data))
                    camera_image.show()

                # 播放音频
                if 'audio' in self.data_buffers:
                    audio_data = self.data_buffers['audio'].pop(0)
                    self.audio_stream.write(audio_data)

            except Exception as e:
                print(f"Error in output_data: {e}")
                break

    def start_conference(self,send_conn):
        '''
        init conns when create or join a conference with necessary conference_info
        and
        start necessary running task for conference
        '''
        try:
            # 启动共享和接收任务
            self.share_switch('screen',send_conn)
            self.share_switch('camera',send_conn)
            self.share_switch('audio',send_conn)

            # 启动输出任务
            threading.Thread(target=self.output_data, daemon=True).start()

        except Exception as e:
            print(f"Error in start_conference: {e}")

    def close_conference(self):
        '''
        close all conns to servers or other clients and cancel the running tasks
        pay attention to the exception handling
        '''
        try:
            # 停止共享任务
            for data_type in list(self.active_shares.keys()):
                self.share_switch(data_type, enable=False)

            # 关闭连接
            for conn in self.connections:
                conn.close()

        except Exception as e:
            print(f"Error in close_conference: {e}")


    def receive_messages(self):
        """ Continuously listen for messages from the server (e.g., cancel) """
        while True:
            try:
                confirmation = self.conns.recv(1024).decode()
                if not confirmation:
                    break
                if "cancel" in confirmation:
                    print("[Info]: Conference has been canceled by the server.")
                    self.on_meeting = False
                    self.conference_id = None
            except Exception as e:
                print(f"[Error]: {e}")
                break


    def start(self):
        """
        execute functions based on the command line input
        """
        try:
            self.conns = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conns.connect(self.server_addr)
            print("[Info]: Connected to server.")
        except Exception as e:
            print(f"[Error]: Unable to connect to server: {e}")
            self.conns = None

        # threading.Thread(target=self.receive_messages, daemon=True).start()

        while True:
            if not self.on_meeting:
                status = 'Free'
            else:
                status = f'OnMeeting-{self.conference_id}'

            recognized = True
            cmd_input = input(f'({status}) Please enter a operation (enter "?" to help): ').strip().lower()
            # cmd_input='create'
            fields = cmd_input.split(maxsplit=1)
            if len(fields) == 1:
                if cmd_input in ('?', '？'):
                    print(HELP)
                elif cmd_input == 'create':
                    self.create_conference()
                elif cmd_input == 'quit':
                    self.quit_conference()
                elif cmd_input == 'cancel':
                    self.cancel_conference()
                elif cmd_input=='ls':
                    self.ls_conference()
                else:
                    recognized = False
            elif len(fields) == 2:
                if fields[0] == 'join':
                    input_conf_id = fields[1]
                    if input_conf_id.isdigit():
                        self.join_conference(input_conf_id)
                    else:
                        print('[Warn]: Input conference ID must be in digital form')
                elif fields[0] == 'switch':
                    data_type = fields[1]
                    if data_type in self.share_data.keys():
                        self.share_switch(data_type)
                else:
                    recognized = False
            else:
                recognized = False

            if not recognized:
                print(f'[Warn]: Unrecognized cmd_input {cmd_input}')


if __name__ == '__main__':
    client1 = ConferenceClient()
    client1.start()

