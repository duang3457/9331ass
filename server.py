import socket
import threading
import time
import sys

# 全局变量和常量
SERVER_HOST = "127.0.0.1"
BUFFER_SIZE = 1024
HEARTBEAT_TIMEOUT = 3

# 数据结构
credentials = {}
active_peers = {}
published_files = {}
user_published = {}

# 加载用户凭证
def load_credentials():
    try:
        with open("credentials.txt", "r") as file:
            for line in file:
                username, password = line.strip().split()
                credentials[username] = password
        print("credentials文件加载完成。")
    except Exception as e:
        print(f"加载credentials文件失败: {e}")
        sys.exit(1)


# 处理客户端请求消息
def handle_client_message(message, client_address, server_socket):
    try:
        parts = message.split()
        command = parts[0]
        requester = parts[1]
        content = parts[2:] if len(parts) > 2 else []

        if command == "AUTH":
            password = content[0]
            if credentials.get(requester) == password and requester not in active_peers:
                active_peers[requester] = {'address': client_address, 'last_heartbeat': time.time()}
                response = "Welcome to BitTrickle!"
            else:
                response = "Authentication failed. Please try again."

        elif command == "HBT":
            if requester in active_peers:
                active_peers[requester]['last_heartbeat'] = time.time()
                response = "Heartbeat received"
            else:
                response = "User not authenticated."

        elif command == "LAP":
            active_users = [user for user in active_peers if user != requester]
            response = "Active peers: " + ", ".join(active_users) if active_users else "No active peers"

        elif command == "PUB":
            filename = content[0]
            published_files.setdefault(filename, []).append(requester)
            user_published.setdefault(requester, []).append(filename)
            response = "File published successfully"

        elif command == "UNP":
            filename = content[0]
            if filename in published_files and requester in published_files[filename]:
                published_files[filename].remove(requester)
                user_published[requester].remove(filename)
                if not published_files[filename]:
                    del published_files[filename]
                response = "File unpublished successfully"
            else:
                response = "File not found or you are not the publisher"

        else:
            response = "ERR Unknown command"

        # 发送响应消息
        server_socket.sendto(response.encode(), client_address)

        # 日志记录
        log_message(client_address, message, response)

    except Exception as e:
        print(f"处理请求失败: {e}")


# 日志记录
def log_message(client_address, message, response):
    log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {client_address} - Command: {message} - Response: {response}"
    print(log_entry)


# 心跳监控线程
def heartbeat_monitor():
    while True:
        current_time = time.time()
        to_remove = []

        for user, data in active_peers.items():
            if current_time - data['last_heartbeat'] > HEARTBEAT_TIMEOUT:
                to_remove.append(user)

        for user in to_remove:
            del active_peers[user]
            print(f"用户 {user} 超时，已下线。")

        time.sleep(1)


# 启动服务器
def start_server(port):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((SERVER_HOST, port))
        print(f"服务器启动成功，监听端口: {port}")

        # 启动心跳监控线程
        threading.Thread(target=heartbeat_monitor, daemon=True).start()

        while True:
            message, client_address = server_socket.recvfrom(BUFFER_SIZE)
            message = message.decode()
            print(f"收到来自 {client_address} 的消息: {message}")

            # 处理客户端消息
            handle_client_message(message, client_address, server_socket)

    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)


# 主程序入口
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python server.py <server_port>")
        sys.exit(1)

    # 加载用户凭证
    load_credentials()

    # 启动服务器
    start_server(int(sys.argv[1]))
