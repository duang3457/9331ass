import socket
import threading
import os
import sys
import time

# 全局变量
SERVER_ADDRESS = "127.0.0.1"
HEARTBEAT_INTERVAL = 2
BUFFER_SIZE = 1024
USERNAME = None

# 客户端初始化
def init_client(server_port):
    global SERVER_ADDRESS, USERNAME
    try:
        # 获取服务器端口
        server_port = int(server_port)
        # 创建 UDP 套接字并连接到服务器
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.connect((SERVER_ADDRESS, server_port))

        # 用户认证
        while True:
            USERNAME = input("请输入用户名: ")
            password = input("请输入密码: ")
            auth_message = f"AUTH {USERNAME} {password}"
            client_socket.send(auth_message.encode())
            response, _ = client_socket.recvfrom(BUFFER_SIZE)
            if response.decode() == "AUTH_SUCCESS":
                print("认证成功！")
                break
            else:
                print("认证失败，请重新输入。")

        # 启动心跳线程
        threading.Thread(target=send_heartbeat, args=(client_socket,)).start()

        # 启动响应监听线程
        threading.Thread(target=listen_to_server, args=(client_socket,)).start()

        # 启动文件传输服务器
        threading.Thread(target=start_file_server).start()

        # 显示可用命令
        print("可用命令：GET, LAP, PUB, LPF, SCH, UNP, XIT")

        # 主命令循环
        while True:
            command = input("请输入命令: ")
            process_command(client_socket, command)

    except Exception as e:
        print(f"客户端初始化失败: {e}")
        sys.exit(1)


# 发送心跳消息
def send_heartbeat(client_socket):
    while True:
        heartbeat_message = f"HBT {USERNAME}"
        client_socket.send(heartbeat_message.encode())
        time.sleep(HEARTBEAT_INTERVAL)


# 监听服务器响应
def listen_to_server(client_socket):
    while True:
        response, _ = client_socket.recvfrom(BUFFER_SIZE)
        print("服务器响应:", response.decode())


# 处理文件下载
def download_file(address, filename):
    try:
        # 使用 TCP 连接到对等节点
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as file_socket:
            file_socket.connect(address)
            file_socket.send(f"GET {filename}".encode())

            # 接收文件内容并保存
            with open(filename, "wb") as f:
                while True:
                    data = file_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    f.write(data)
            print(f"文件 {filename} 下载成功。")
    except Exception as e:
        print(f"下载文件失败: {e}")


# 处理客户端命令
def process_command(client_socket, command):
    parts = command.strip().split()
    cmd = parts[0].upper()
    if cmd == "GET" and len(parts) == 2:
        filename = parts[1]
        client_socket.send(f"GET {filename}".encode())

    elif cmd == "LAP":
        client_socket.send(f"LAP {USERNAME}".encode())

    elif cmd == "PUB" and len(parts) == 2:
        filename = parts[1]
        if os.path.exists(filename):
            client_socket.send(f"PUB {USERNAME} {filename}".encode())
        else:
            print("文件不存在。")

    elif cmd == "LPF":
        client_socket.send(f"LPF {USERNAME}".encode())

    elif cmd == "SCH" and len(parts) == 2:
        filename = parts[1]
        client_socket.send(f"SCH {USERNAME} {filename}".encode())

    elif cmd == "UNP" and len(parts) == 2:
        filename = parts[1]
        client_socket.send(f"UNP {USERNAME} {filename}".encode())

    elif cmd == "XIT":
        print("Goodbye!")
        # client_socket.send("XIT".encode())
        client_socket.close()
        sys.exit(0)

    else:
        print("无效命令，请重新输入。")


# 启动文件传输服务器
def start_file_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_ADDRESS, 0))  # 随机端口
    server_socket.listen(5)
    print(f"文件传输服务器启动，监听端口: {server_socket.getsockname()[1]}")

    while True:
        conn, addr = server_socket.accept()
        threading.Thread(target=handle_file_request, args=(conn,)).start()


# 处理文件请求
def handle_file_request(conn):
    try:
        request = conn.recv(BUFFER_SIZE).decode()
        parts = request.split()
        if len(parts) == 2 and parts[0] == "GET":
            filename = parts[1]
            if os.path.exists(filename):
                with open(filename, "rb") as f:
                    data = f.read(BUFFER_SIZE)
                    while data:
                        conn.send(data)
                        data = f.read(BUFFER_SIZE)
                print(f"已发送文件 {filename}")
            else:
                print("请求的文件不存在")
        conn.close()
    except Exception as e:
        print(f"处理文件请求失败: {e}")
        conn.close()


# 主函数
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python client.py <server_port>")
        sys.exit(1)

    init_client(sys.argv[1])
