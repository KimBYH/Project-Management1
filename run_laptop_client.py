"""
run_laptop_client.py - 노트북 전용 접속 클라이언트 런처
(데스크탑 IP 기본 추천 및 원클릭 접속 지원)
"""
import sys
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 현재 데스크탑의 LAN IP (필요 시 수정 가능)
DEFAULT_DESKTOP_IP = "10.71.131.41"
DEFAULT_PORT = 9999


def main():
    print("=" * 60)
    print("💻 [노트북 클라이언트] 데스크탑 서버 접속 준비...")
    print(f"👉 기본 연결 대상 IP: {DEFAULT_DESKTOP_IP}:{DEFAULT_PORT}")
    print("=" * 60)

    # GUI 클라이언트를 접속 다이얼로그와 함께 실행 (데스크탑 IP를 기본값으로 주입)
    subprocess.Popen([
        sys.executable, "gui_client.py",
        "--host", DEFAULT_DESKTOP_IP,
        "--port", str(DEFAULT_PORT),
        "--nick", "Laptop_Player",
        "--x", "200",
        "--y", "120"
    ], cwd=".")

    print("\n[✔] 접속 설정 창이 열렸습니다. 서버 IP를 확인 후 [접속하기]를 눌러주세요!\n")


if __name__ == "__main__":
    main()
