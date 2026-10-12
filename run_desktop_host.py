"""
run_desktop_host.py - 데스크탑 전용 호스트 런처
(서버 자동 가동 + 데스크탑용 GUI 플레이어 실행 + 노트북 접속 IP 친절 안내)
"""
import sys
import time
import socket
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def is_server_running(host="127.0.0.1", port=9999):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def main():
    lan_ip = get_lan_ip()

    print("=" * 65)
    print("🖥️  [데스크탑 호스트] UP & DOWN 서버 및 플레이어 1 가동 중...")
    print("=" * 65)

    # 1. 서버 실행 확인 및 자동 기동
    if not is_server_running():
        print("[*] 게임 서버를 백그라운드로 실행합니다...")
        subprocess.Popen([sys.executable, "server.py", "--host", "0.0.0.0", "--port", "9999"], cwd=".")
        time.sleep(1.0)
    else:
        print("[+] 기존 게임 서버가 이미 가동 중입니다.")

    # 2. 데스크탑용 플레이어 1 GUI 창 실행
    print("[*] 데스크탑용 GUI 클라이언트(Player1)를 실행합니다...")
    subprocess.Popen([
        sys.executable, "gui_client.py",
        "--host", "127.0.0.1",
        "--port", "9999",
        "--nick", "Desktop_Player",
        "--x", "80",
        "--y", "100",
        "--quick"
    ], cwd=".")

    print("\n" + "★" * 65)
    print(f"📢 [노트북 연결 안내]")
    print(f"👉 노트북에서 접속할 데스크탑 IP : {lan_ip}")
    print(f"👉 포트 번호                     : 9999")
    print(f"👉 노트북에서는 'py run_laptop_client.py' 또는 'py gui_client.py'를 실행해주세요!")
    print("★" * 65 + "\n")


if __name__ == "__main__":
    main()
