from functions import connection_establish, server_message_encrypt, server_response, SUCCESS

if __name__ == '__main__':
    print("欢迎使用Telnet服务")
    while True:
        ip_port = input("请输入要登录的主机{IP:port} or {exit} to leave：")
        if ip_port == "exit":
            break

        ## Task 1.1
        established_client, info = connection_establish(ip_port)
        print(info)
        ## Task 1.1

        if established_client:
            while True:
                local_ip, local_port = established_client.getsockname()
                # cmd = input(f"{ip_port}:").strip()
                cmd = input(f"{local_ip}:{local_port}: ").strip()
                if not cmd:
                    continue
                ## Task 3.1
                encrypted_cmd, pwd_hash = server_message_encrypt(cmd)
                ## Task 3.1
                established_client.send(encrypted_cmd.encode("utf-8"))
                ## Task 3.4
                recv_data = server_response(established_client, pwd_hash).decode("utf-8")
                ## Task 3.4
                print(f"{ip_port}: {recv_data}")
                if recv_data == SUCCESS('disconnected'):
                    break
            established_client.close()
            break
    print("欢迎下次使用")
