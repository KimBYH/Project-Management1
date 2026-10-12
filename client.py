"""
client.py - 1~100 UP/DOWN 2인 대결 및 실시간 채팅 콘솔(CLI) 클라이언트
"""
import sys
import socket
import threading
import argparse
from protocol import MessageStream

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class ConsoleGameClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9999, nickname: str = "Player"):
        self.host = host
        self.port = port
        self.nickname = nickname
        self.stream = None
        self.is_running = True
        self.is_my_turn = False
        self.opponent_name = "상대방"

    def connect(self) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"[*] 서버({self.host}:{self.port})에 접속 중...")
            sock.connect((self.host, self.port))
            self.stream = MessageStream(sock)
            print("[+] 접속 성공! 대기실로 입장합니다.\n")
            return True
        except ConnectionRefusedError:
            print("[오류] 서버가 실행 중이지 않습니다. 먼저 'py server.py'를 실행해주세요.")
            return False

    def receive_loop(self):
        """서버로부터 메시지를 실시간으로 수신하는 스레드"""
        try:
            while self.is_running:
                msg = self.stream.recv()
                if msg is None:
                    print("\n[알림] 서버와의 연결이 종료되었습니다.")
                    self.is_running = False
                    break

                m_type = msg.get("type")

                if m_type == "WAITING":
                    print(f"⏳ {msg.get('message')}")

                elif m_type == "MATCH_FOUND":
                    self.opponent_name = msg.get("opponent")
                    turn = msg.get("current_turn")
                    self.is_my_turn = (turn == self.nickname)
                    print("\n" + "=" * 50)
                    print(f"🎉 2인 매칭 완료! 상대방: [{self.opponent_name}]")
                    print(f"👉 선공 플레이어: [{turn}]")
                    print("💡 팁: 일반 입력은 '채팅', '/g [숫자]' 또는 숫자만 입력하면 '추측'입니다.")
                    print("=" * 50)
                    self.print_turn_prompt()

                elif m_type == "CHAT":
                    sender = msg.get("sender")
                    text = msg.get("message")
                    if sender != self.nickname:
                        print(f"\n💬 [{sender}]: {text}")
                        self.print_turn_prompt()

                elif m_type == "GUESS_RESULT":
                    hint = msg.get("message")
                    round_over = msg.get("round_over")
                    next_turn = msg.get("current_turn")
                    scores = msg.get("scores", {})

                    print(f"\n📢 {hint}")
                    if round_over:
                        print(f"📊 현재 스코어: {scores}")
                        print("🔄 다시 시작하려면 '/r' 또는 '재시작'을 입력하세요.")
                        self.is_my_turn = False
                    else:
                        self.is_my_turn = (next_turn == self.nickname)
                    self.print_turn_prompt()

                elif m_type == "ROUND_START":
                    turn = msg.get("current_turn")
                    self.is_my_turn = (turn == self.nickname)
                    print(f"\n🔔 {msg.get('message')}")
                    self.print_turn_prompt()

                elif m_type == "OPPONENT_LEFT":
                    print(f"\n❌ {msg.get('message')}")
                    self.is_running = False
                    break

                elif m_type == "ERROR":
                    print(f"\n⚠️ [서버 안내] {msg.get('message')}")
                    self.print_turn_prompt()

        except Exception:
            pass

    def print_turn_prompt(self):
        if self.is_my_turn:
            print("\n[내 턴 🟢] (1~100 숫자 추측 또는 채팅) > ", end="", flush=True)
        else:
            print("\n[상대 턴 ⏳] (채팅 입력 가능) > ", end="", flush=True)

    def run(self):
        if not self.connect():
            return

        # 닉네임 전송
        self.stream.send({"type": "LOGIN", "nickname": self.nickname})

        # 수신 스레드 시작
        threading.Thread(target=self.receive_loop, daemon=True).start()

        # 사용자 입력 루프
        try:
            while self.is_running:
                user_input = input().strip()
                if not self.is_running:
                    break
                if not user_input:
                    continue

                if user_input.lower() in ["/q", "quit", "exit"]:
                    self.stream.send({"type": "QUIT"})
                    break

                elif user_input in ["/r", "재시작"]:
                    self.stream.send({"type": "RESTART"})
                    continue

                # 숫자 입력인 경우
                if user_input.isdigit():
                    num = int(user_input)
                    self.stream.send({"type": "GUESS", "number": num})
                elif user_input.startswith("/g ") and user_input[3:].strip().isdigit():
                    num = int(user_input[3:].strip())
                    self.stream.send({"type": "GUESS", "number": num})
                else:
                    # 채팅 메시지로 전송 (심리전)
                    self.stream.send({"type": "CHAT", "message": user_input})

        except KeyboardInterrupt:
            print("\n[!] 게임을 종료합니다.")
        finally:
            self.is_running = False
            if self.stream:
                self.stream.close()


def main():
    parser = argparse.ArgumentParser(description="UP/DOWN 2인 대결 및 채팅 콘솔 클라이언트")
    parser.add_argument("--host", default="127.0.0.1", help="서버 IP")
    parser.add_argument("--port", type=int, default=9999, help="서버 포트")
    parser.add_argument("--nick", default="Player", help="플레이어 닉네임")
    args = parser.parse_args()

    client = ConsoleGameClient(host=args.host, port=args.port, nickname=args.nick)
    client.run()


if __name__ == "__main__":
    main()
