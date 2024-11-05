import hmac
import os
import socket
import hashlib
import re
import random
import ast
import fileinput
from sys import excepthook

host = "localhost"
port = 6016
user_inf_txt = 'users.txt'

login_commands = [
    '?',
    'help',
    'exit',
    'logout',
    'changepwd {newpassword}',
    'sum [a] [b] ...',
    'sub [a] [b]',
    'multiply [a] [b] ...',
    'divide [a] [b]'
]


def SUCCESS(message):
    """
    This function is designed to be easy to test, so do not modify it
    """
    return '\n200:' + message


def FAILURE(message):
    """
    This function is designed to be easy to test, so do not modify it
    """
    return '400:' + message


def ntlm_hash_func(password):
    """
    This function is used to encrypt passwords by the MD5 algorithm
    """
    # 1. Convert password to hexadecimal format
    hex_password = ''.join(format(ord(char), '02x') for char in password)

    # 2. Unicode encoding of hexadecimal passwords
    unicode_password = hex_password.encode('utf-16le')

    # 3. The MD5 digest algorithm is used to Hash the Unicode encoded data
    md5_hasher = hashlib.md5()
    md5_hasher.update(unicode_password)

    # Returns the MD5 Hash
    return md5_hasher.hexdigest()


def connection_establish(ip_p):
    """
    Task 1.1 Correctly separate the IP address from the port number in the string
    Returns the socket object of the connected server when the socket server address pointed to by IP:port is available
    Otherwise, an error message is given
    :param ip_p: str 'IP:port'
    :return socket_client: socket.socket() or None
    :return information: str 'success' or error information
    """
    try:
        ip,port=ip_p.split(':')
        port = int(port)
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_client.connect((ip, port))
        return socket_client,'success'
    except ValueError:
        return None, 'Invalid IP:port format'
    except socket.gaierror:
        return None, 'Invalid IP address'
    except socket.error:
        return None, 'Connection failed'
    except Exception:
        return None, 'an error occurred'

    # TODO: finish the codes
    

def load_users(user_records_txt):
    """
    Task 2.1 Load saved user information (username and password)
    :param user_records_txt: a txt file containing username and password records
    :return users: dict {'username':'password'}
    """
    # TODO: finish the codes
    users = {}
    if not os.path.exists(user_records_txt):
        # Create an empty file if it doesn't exist
        with open(user_records_txt, 'w') as file:
            file.write("# This is the user records file.\n# Format: username:password\n")
        print(f"{user_records_txt} not found. A new file has been created.")

    # Open the file in read mode
    with open(user_records_txt, 'r') as file:
        for line in file:
            # Strip whitespace and split by any separator (e.g., comma, space, etc.)
            line = line.strip()
            if line and not line.startswith("#"):  # Ensure line is not empty
                username, password = line.split(':')  # assuming "username:password" format
                users[username] = password

    return users


def user_register(cmd, users):
    """
    Task 2.2 Register command processing
    :param cmd: Instruction string
    :param users: The dict to hold information about all users
    :return feedback message: str
    """
    # TODO: finish the codes

    # Extract username and password
    username = cmd[1]
    password = cmd[2]

    # Check if username already exists
    if username in users:
        return f"Username '{username}' already exists. Please choose a different username."

    with open(user_inf_txt, 'a') as file:
        file.write(f"{username}:{password}\n")

    # Register the new user
    users[username] = password
    return f"User '{username}' registered successfully."

def login_authentication(conn, cmd, users):
    """
    Task 2.3 Login authentication
        You can simply use password comparison for authentication (Task 2.3 basic score)
        It can also be implemented according to the NTLM certification process to obtain Task 3.2 and 3.5 scores
    :param conn: socket connection to the client
    :param cmd: Instruction string
    :param users: The dict to hold information about all users
    :return: feedback message: str, login_user: str
    """
    # TODO: finish the codes
    # 提取用户名
    username = cmd[1]

    # 检查用户名是否存在
    if username in users:
        # 获取该用户的 MD5 加密密码
        password_hash = users[username]

        # 生成一个随机挑战
        challenge = generate_challenge()

        # 将挑战发送给客户端
        conn.send(challenge)

        # 接收客户端发送回来的加密响应
        client_response = conn.recv(1024)

        # 服务器计算预期的响应
        expected_response = calculate_response(password_hash, challenge)

        # 比较客户端的响应和服务器的预期响应
        if client_response == expected_response:
            feedback = f"User '{username}' logged in successfully."
            # conn.send(feedback.encode())  # 发送成功消息给客户端
            return feedback, username
        else:
            feedback = "password wrong,try again."
            # conn.send(feedback.encode())  # 发送失败消息给客户端
            return feedback, None
    else:
        feedback = "Invalid username,please register first."
        # conn.send(feedback.encode())  # 用户名不存在时发送失败消息
        return feedback, None

def server_message_encrypt(message):
    """
    Task 3.1 Determine whether the command is "login", "register", or "changepwd",
    If so, it encrypts the password in the command and returns the encrypted message and Password
    Otherwise, the original message and None are returned
    :param message: str message sent to server:
    :return encrypted message: str, encrypted password: str
    """
    # TODO: finish the codes
    # Split the command to identify its components
    parts = message.split()

    # Check if the command is one of the target commands and if it has the right number of parts
    if len(parts) == 3 and parts[0] in {"login", "register", "changepwd"}:
        # Extract the username and password
        username = parts[1]
        password = parts[2]

        # Encrypt the password using MD5
        encrypted_password = ntlm_hash_func(password)

        # Construct the new command with the encrypted password
        encrypted_cmd = f"{parts[0]} {username} {encrypted_password}"

        # Return the encrypted message and the encrypted password
        return encrypted_cmd, encrypted_password
    else:
        # If not a target command, return the original message and None
        return message, None

    

def generate_challenge():
    """
    Task 3.2
    :return information: bytes random bytes as challenge message
    """
    # TODO: finish the codes
    challenge_message = os.urandom(8)

    return challenge_message


def calculate_response(ntlm_hash, challenge):
    """
    Task 3.3
    :param ntlm_hash: str encrypted password
    :param challenge: bytes random bytes as challenge message
    :return expected response
    """
    # TODO: finish the codes
    # Convert the MD5 hash (hex string) to bytes

    key = bytes.fromhex(ntlm_hash)

    # Create HMAC-SHA256 object with the key and challenge message
    hmac_obj = hmac.new(key, msg=challenge, digestmod=hashlib.sha256)

    # Return the HMAC-SHA256 digest (expected response)
    return hmac_obj.digest()

    

def server_response(server, password_hash):
    """
    Task 3.4 Receives the server response and determines whether the message returned by the server is an authentication challenge.
    If it is, the challenge will be authenticated with the encrypted password, and the authentication information will be returned to the server to obtain the login result
    Otherwise, the original message is returned
    :param server: socket server
    :param password_hash: encrypted password
    :return server response: str
    """
    # TODO: finish the codes
    challenge_message = server.recv(1024)

    # Check if the message is a challenge (in this case, let's assume the challenge is a bytes message of length 8)
    if len(challenge_message) == 8:
        # Generate the response using HMAC-SHA256 with the challenge and password hash
        response = calculate_response(password_hash, challenge_message)

        # Send the response back to the server
        server.send(response)

        # Wait for the server to send the authentication result
        auth_result = server.recv(1024)
        return auth_result

    # If it's not a challenge, return the original message (assume it's a string)
    return challenge_message


def login_cmds(receive_data, users, login_user):
    """
    Task 4 Command processing after login
    :param receive_data: Received user commands
    :param users: The dict to hold information about all users
    :param login_user: The logged-in user
    :return feedback message: str, login user: str
    """
    # TODO: finish the codes
    feedback_data = ""

    # 将用户命令拆分成列表
    cmd = receive_data.split()

    # 判断是否有命令输入
    if not cmd:
        feedback_data = "No command entered."
        return feedback_data, login_user

    # 1. 加法处理
    if cmd[0] == "sum":
        try:
            numbers = map(float, cmd[1:])  # 将后面的参数转换为数字
            result = sum(numbers)
            feedback_data = f"Result of addition: {result}"
        except ValueError:
            feedback_data = "Please enter valid numbers for addition."

    # 2. 乘法处理
    elif cmd[0] == "multiply":
        try:
            numbers = map(float, cmd[1:])  # 将后面的参数转换为数字
            result = 1
            for num in numbers:
                result *= num
            feedback_data = f"Result of multiplication: {result}"
        except ValueError:
            feedback_data = "Please enter valid numbers for multiplication."

    # 3. 减法处理
    elif cmd[0] == "subtract":
        if len(cmd) != 3:
            feedback_data = "Subtraction requires exactly two numbers."
        else:
            try:
                num1, num2 = float(cmd[1]), float(cmd[2])
                result = num1 - num2
                feedback_data = f"Result of subtraction: {result}"
            except ValueError:
                feedback_data = "Please enter valid numbers for subtraction."

    # 4. 除法处理
    elif cmd[0] == "divide":
        if len(cmd) != 3:
            feedback_data = "Division requires exactly two numbers."
        else:
            try:
                num1, num2 = float(cmd[1]), float(cmd[2])
                if num2 == 0:
                    feedback_data = "Division by zero is not allowed."
                else:
                    result = num1 / num2
                    feedback_data = f"Result of division: {result}"
            except ValueError:
                feedback_data = "Please enter valid numbers for division."

    # 5. 修改密码
    elif cmd[0] == "changepwd":
        if len(cmd) != 2:
            feedback_data = "Please provide the new password."
        else:
            new_password = cmd[1]
            users[login_user] = ntlm_hash_func(new_password)  # 假设用户信息以字典形式存储
            with open(user_inf_txt, 'w') as f:
                # 遍历更新后的 users 字典并写入文件
                for username, password in users.items():
                    # password = ntlm_hash_func(password)
                    # f.write(f"{username}:{password}\n")
                    f.write(f"{username}:{password}\n")
            feedback_data = "Password changed successfully."

    # 6. 显示帮助信息
    elif cmd[0] == "?" or cmd[0] == "help" or  cmd[0] == 'ls':
        feedback_data = '\nAvailable commends: \n\t' + '\n\t'.join(login_commands)
        # feedback_data = SUCCESS(feedback_data)

    # 7. 断开连接
    elif cmd[0] == "exit":
        feedback_data = "200:disconnected"
        login_user = None  # 清空登录用户

    # 8. 注销登录
    elif cmd[0] == "logout":
        feedback_data = "Logged out successfully."
        login_user = None  # 清空登录用户信息

    elif cmd[0] == "login":
        feedback_data = "you have login already.Type '?' or 'help' for available commands."

    # 未知命令
    else:
        feedback_data = "Invalid command. Type '?' or 'help' for available commands."

    return feedback_data, login_user