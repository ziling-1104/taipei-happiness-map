# start.py
# -*- coding: utf-8 -*-
import socket
import subprocess


def find_free_port(start=5050):
    """找一個沒被占用的 port"""
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1


if __name__ == "__main__":
    port = find_free_port()
    print(f"▶ 自動選擇可用 port：{port}")
    print(f"🚀 啟動中：http://127.0.0.1:{port}")
    print(f"🚀 啟動 Flask：正在載入資料中……")

    # 呼叫 app.py，並將 port 傳入
    subprocess.run(["python3", "app.py", str(port)])
