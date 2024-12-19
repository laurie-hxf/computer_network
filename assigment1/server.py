import socketserver
import time
import threading

from functions import *

commands = [
    '?',
    'help',
    'exit',
    'login {name} {password}',
    'register {name} {password}'
]

### Task 2.1 Read user information files
users = load_users(user_inf_txt)
print(users)
## Task 2.1

def save_command_to_file(command, client_address):
    with open('user_commands.txt', 'a') as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        f.write(f"{timestamp} - {client_address} - {command}\n")

def main_loop(socket_conn, client_address, login_user):
    """
    :param socket_conn: socket connection
    :param client_address: client IP address
    :param login_user: str current logged-in user
    :return continue flag: boolean for main loop continue judgement, login user: str
    """
    ## Task 1.3
    # TODO: finish the codes
    receive_data = socket_conn.recv(1024).decode('UTF-8')
    ## Task 1.3
    if not receive_data:
        print(f"Connection closed by {client_address}")
        return False, None

    save_command_to_file(receive_data, client_address)

        # Command processing before login
    if not login_user:
        # Command processing without arguments
        if receive_data == '?' or receive_data == 'help' or receive_data == 'ls':
            feedback_data = 'Available commends: \n\t' + '\n\t'.join(commands)
            feedback_data = SUCCESS(feedback_data)
        elif receive_data == 'exit':
            feedback_data = 'disconnected'
            feedback_data = SUCCESS(feedback_data)
        else:
            # Command processing with arguments
            cmd = receive_data.split(' ')
            if cmd[0] == 'login':
                if len(cmd) < 3:
                    feedback_data = 'Please re-enter the login commend with your username and password'
                    feedback_data = FAILURE(feedback_data)
                elif len(cmd) == 3:
                    ## Task 2.3, 3.2, 3.5
                    feedback_data, login_user = login_authentication(socket_conn, cmd, users)
                    ## Task 2.3, 3.2, 3.5
                else:
                    feedback_data = "Password shouldn't include spaces"
                    feedback_data = FAILURE(feedback_data)
            elif cmd[0] == 'register':
                if len(cmd) < 3:
                    feedback_data = 'Please re-enter the command with username and password'
                    feedback_data = FAILURE(feedback_data)
                elif len(cmd) > 3:
                    feedback_data = "Username or password shouldn't include spaces"
                    feedback_data = FAILURE(feedback_data)
                else:
                    ## Task 2.2
                    feedback_data = user_register(cmd, users)
                    ## Task 2.2
            else:
                feedback_data = "Invalid command"
                feedback_data = FAILURE(feedback_data)
    else:
        ## Task 4
        feedback_data, login_user = login_cmds(receive_data, users, login_user)
        print(feedback_data)
        # socket_conn.sendall(feedback_data.encode('UTF-8'))
        ## Task 4

    socket_conn.sendall(feedback_data.encode('UTF-8'))
    if feedback_data == '200:disconnected':
        return False, None
    return True, login_user


## Task 1.2
## Connection establishment on server
# TODO: finish the codes
## Task 1.2

def start_server():
    sever_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sever_socket.bind(('127.0.0.1', port))
    sever_socket.listen(5)
    while True:
        client_socket, client_address = sever_socket.accept()
        client_thread = threading.Thread(target=client_session, args=(client_socket, client_address))
        client_thread.start()#socket_conn, client_address, login_user


def client_session(client_socket, client_address):
    # 初始化每个客户端连接的 `login_user` 状态为 None
    login_user = None
    connected = True

    while connected:
        # 调用 `main_loop` 并更新 `login_user`
        connected, login_user = main_loop(client_socket, client_address, login_user)

    # 关闭客户端连接
    client_socket.close()
    print(f"Connection with {client_address} closed.")


if __name__ == '__main__':
    start_server()
    # sever_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sever_socket.bind(('127.0.0.1', port))
    # sever_socket.listen(5)
    # client_socket, client_address = sever_socket.accept()
    # client_session(client_socket, client_address)


