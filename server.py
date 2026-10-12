"""
server.py - 1~100 UP/DOWN 2인 대결 및 실시간 채팅 TCP 소켓 서버
"""
import sys
import socket
import threading
import argparse
import logging
from typing import Dict, Optional, Tuple
from protocol import MessageStream
from game_logic import TwoPlayerGameRoom

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("GameServer")


class ClientSession:
    def __init__(self, sock: socket.socket, addr: Tuple[str, int], nickname: str):
        self.sock = sock
        self.addr = addr
        self.nickname = nickname
        self.stream = MessageStream(sock)
        self.room: Optional['GameRoomHandler'] = None


class GameRoomHandler:
    """
    2인의 플레이어를 연결하여 게임 진행 및 실시간 채팅을 중계하는 핸들러
    """

    def __init__(self, room_id: str, p1: ClientSession, p2: ClientSession):
        self.room_id = room_id
        self.p1 = p1
        self.p2 = p2
        self.p1.room = self
        self.p2.room = self
        self.lock = threading.Lock()
        self.game = TwoPlayerGameRoom(room_id, p1.nickname, p2.nickname)

    def broadcast(self, payload: dict):
        """방 내 두 플레이어 모두에게 메시지 전송"""
        with self.lock:
            try:
                self.p1.stream.send(payload)
            except Exception:
                pass
            try:
                self.p2.stream.send(payload)
            except Exception:
                pass

    def start_game(self):
        """매칭 완료 후 양측에 시작 메시지 전송"""
        logger.info(f"[{self.room_id}] 매칭 시작: {self.p1.nickname} VS {self.p2.nickname}")
        self.p1.stream.send({
            "type": "MATCH_FOUND",
            "room_id": self.room_id,
            "you": self.p1.nickname,
            "opponent": self.p2.nickname,
            "current_turn": self.game.current_turn,
            "round": self.game.round_number,
            "message": f"매칭 성공! 상대는 [{self.p2.nickname}]님입니다."
        })
        self.p2.stream.send({
            "type": "MATCH_FOUND",
            "room_id": self.room_id,
            "you": self.p2.nickname,
            "opponent": self.p1.nickname,
            "current_turn": self.game.current_turn,
            "round": self.game.round_number,
            "message": f"매칭 성공! 상대는 [{self.p1.nickname}]님입니다."
        })

    def handle_chat(self, sender: ClientSession, message: str):
        """채팅 메시지 브로드캐스트 (심리전)"""
        logger.info(f"[{self.room_id} 채팅] {sender.nickname}: {message}")
        self.broadcast({
            "type": "CHAT",
            "sender": sender.nickname,
            "message": message
        })

    def handle_guess(self, sender: ClientSession, number: int):
        """숫자 추측 처리"""
        with self.lock:
            result = self.game.guess(sender.nickname, number)

            if result.get("type") == "ERROR":
                sender.stream.send(result)
                return

            logger.info(
                f"[{self.room_id}] {sender.nickname} 추측: {number} -> "
                f"{result.get('status')} (정답: {self.game.target_number if result.get('round_over') else '비공개'})"
            )
            # 모든 플레이어에게 추측 결과 전송
            self.broadcast(result)

    def handle_restart(self, sender: ClientSession):
        """재시작 요청 처리"""
        with self.lock:
            both_ready, msg = self.game.vote_restart(sender.nickname)
            if both_ready:
                logger.info(f"[{self.room_id}] 새 라운드 시작 (목표 숫자: {self.game.target_number})")
                self.broadcast({
                    "type": "ROUND_START",
                    "round": self.game.round_number,
                    "current_turn": self.game.current_turn,
                    "scores": self.game.scores,
                    "message": f"🎲 [라운드 {self.game.round_number}] 새 게임이 시작되었습니다!"
                })
            else:
                self.broadcast({
                    "type": "CHAT",
                    "sender": "시스템",
                    "message": msg
                })

    def handle_disconnect(self, disconnected_sender: ClientSession):
        """한 플레이어가 퇴장했을 때 상대방에게 알림"""
        other = self.p2 if disconnected_sender == self.p1 else self.p1
        logger.info(f"[{self.room_id}] {disconnected_sender.nickname} 퇴장 -> {other.nickname}에게 알림")
        try:
            other.stream.send({
                "type": "OPPONENT_LEFT",
                "message": f"상대방 [{disconnected_sender.nickname}]님이 퇴장했습니다. 게임이 종료됩니다."
            })
        except Exception:
            pass


def get_lan_ip() -> str:
    """외부 장치(노트북 등)에서 접속할 수 있는 현재 머신의 로컬 IP를 확인합니다."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class UpDownServer:
    """
    UP/DOWN 2인 매칭 및 멀티스레드 소켓 서버
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 9999):
        self.host = host
        self.port = port
        self.server_sock = None
        self.is_running = False
        self.waiting_client: Optional[ClientSession] = None
        self.waiting_lock = threading.Lock()
        self.room_counter = 1

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        lan_ip = get_lan_ip()
        try:
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(10)
            self.is_running = True
            logger.info("=" * 65)
            logger.info(f"🎮 UP/DOWN 2인 대결 & 채팅 서버 가동 완료!")
            logger.info(f"  💻 이 데스크탑에서 접속할 주소: 127.0.0.1:{self.port}")
            logger.info(f"  📱 다른 노트북에서 접속할 주소: {lan_ip}:{self.port}")
            logger.info("플레이어 접속을 대기하고 있습니다... (Ctrl+C 종료)")
            logger.info("=" * 65)

            while self.is_running:
                try:
                    client_sock, client_addr = self.server_sock.accept()
                    logger.info(f"[신규 연결] {client_addr}")
                    threading.Thread(
                        target=self.client_entry_thread,
                        args=(client_sock, client_addr),
                        daemon=True
                    ).start()
                except OSError:
                    break

        except KeyboardInterrupt:
            logger.info("서버 종료 신호 수신.")
        finally:
            self.stop()

    def stop(self):
        self.is_running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass
        logger.info("서버가 안전하게 종료되었습니다.")

    def client_entry_thread(self, client_sock: socket.socket, client_addr: tuple):
        stream = MessageStream(client_sock)
        try:
            # 1. LOGIN 메시지 수신
            login_msg = stream.recv()
            if not login_msg or login_msg.get("type") != "LOGIN":
                stream.close()
                return

            nickname = str(login_msg.get("nickname", f"User_{client_addr[1]}")).strip() or "User"
            session = ClientSession(client_sock, client_addr, nickname)

            # 2. 2인 매칭 큐 처리
            room = None
            with self.waiting_lock:
                if self.waiting_client is None:
                    # 대기자 등록
                    self.waiting_client = session
                    logger.info(f"[{nickname}] 대기 큐 등록 (1/2)")
                    session.stream.send({
                        "type": "WAITING",
                        "message": "상대 플레이어의 접속을 대기하고 있습니다... (1/2)"
                    })
                else:
                    # 매칭 성사!
                    p1 = self.waiting_client
                    p2 = session
                    self.waiting_client = None

                    # 동일 닉네임 방지
                    if p1.nickname == p2.nickname:
                        p2.nickname += "_2"

                    room_id = f"Room_{self.room_counter}"
                    self.room_counter += 1
                    room = GameRoomHandler(room_id, p1, p2)

            if room:
                room.start_game()

            # 3. 클라이언트 메시지 루프
            while self.is_running:
                msg = stream.recv()
                if msg is None:
                    break

                msg_type = msg.get("type")
                current_room = session.room

                if msg_type == "CHAT" and current_room:
                    chat_text = str(msg.get("message", "")).strip()
                    if chat_text:
                        current_room.handle_chat(session, chat_text)

                elif msg_type == "GUESS" and current_room:
                    number = msg.get("number")
                    current_room.handle_guess(session, number)

                elif msg_type == "RESTART" and current_room:
                    current_room.handle_restart(session)

                elif msg_type == "QUIT":
                    break

        except (ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            logger.error(f"[{client_addr}] 오류: {e}")
        finally:
            with self.waiting_lock:
                if self.waiting_client == session:
                    self.waiting_client = None
            if session.room:
                session.room.handle_disconnect(session)
            stream.close()
            logger.info(f"[{session.nickname}] 소켓 연결 해제 완료.")


def main():
    parser = argparse.ArgumentParser(description="UP/DOWN 2인 대결 & 채팅 소켓 서버")
    parser.add_argument("--host", default="0.0.0.0", help="바인딩할 호스트 IP (기본: 0.0.0.0, 모든 인터페이스 허용)")
    parser.add_argument("--port", type=int, default=9999, help="포트 번호 (기본: 9999)")
    args = parser.parse_args()

    server = UpDownServer(host=args.host, port=args.port)
    server.start()


if __name__ == "__main__":
    main()
