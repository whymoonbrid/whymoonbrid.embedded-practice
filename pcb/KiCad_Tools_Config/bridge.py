import subprocess
import sys
import threading

# 你的 konnect.exe 绝对路径
EXE_PATH = r"C:\Users\moonbrid\AppData\Local\konnect\cache\konnect.exe"

def forward_stdin():
    while True:
        data = sys.stdin.buffer.read(1)
        if not data:
            break
        process.stdin.write(data)
        process.stdin.flush()

def forward_stdout():
    while True:
        data = process.stdout.read(1)
        if not data:
            break
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

# 启动 konnect.exe，接管它的输入输出
process = subprocess.Popen([EXE_PATH], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)

# 启动两个线程做双向数据转发
threading.Thread(target=forward_stdin, daemon=True).start()
threading.Thread(target=forward_stdout, daemon=True).start()

process.wait()