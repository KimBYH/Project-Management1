"""
run_dual_gui.py - 2개의 GUI 창과 서버를 원클릭으로 실행하는 런처 스크립트
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


def is_server_running(host="127.0.0.1", port=9999):
    """서버 소켓이 열려있는지 확인"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def main():
    print("=" * 60)
    print("🚀 [원클릭 런처] UP & DOWN 2인 심리전 GUI 환경을 준비합니다...")
    print("=" * 60)

    # 1. 서버 실행 확인 및 자동 기동
    if not is_server_running():
        print("[*] 서버가 실행 중이지 않아 새로 시작합니다...")
        subprocess.Popen([sys.executable, "server.py"], cwd=".")
        time.sleep(1.0)
    else:
        print("[+] 기존 서버가 이미 실행 중입니다.")

    # 2. 플레이어 1 GUI 창 실행 (화면 좌측)
    print("[*] 플레이어 1 (Player1) GUI 창을 실행합니다...")
    p1 = subprocess.Popen([
        sys.executable, "gui_client.py",
        "--nick", "Player1",
        "--x", "40",
        "--y", "80",
        "--quick"
    ], cwd=".")

    time.sleep(0.5)

    # 3. 플레이어 2 GUI 창 실행 (화면 우측)
    print("[*] 플레이어 2 (Player2) GUI 창을 실행합니다...")
    p2 = subprocess.Popen([
        sys.executable, "gui_client.py",
        "--nick", "Player2",
        "--x", "830",
        "--y", "80",
        "--quick"
    ], cwd=".")

    print("\n[✔] 두 개의 GUI 창이 화면 좌우에 나란히 실행되었습니다!")
    print("👉 채팅창에 'Player1 : ㅋㅋㅋㅋㅋㅋ' / 'Player2 : 뭘 웃어?' 등을 입력하며 심리전을 즐겨보세요!\n")


if __name__ == "__main__":
    main()
