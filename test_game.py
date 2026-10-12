"""
test_game.py - UP/DOWN 미니 게임 단위 테스트 및 2인 대결/채팅 소켓 통합 테스트
"""
import sys
import unittest
import socket
import threading
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from protocol import MessageStream
from game_logic import UpDownGame, TwoPlayerGameRoom
from server import UpDownServer


class TestUpDownGameLogic(unittest.TestCase):
    """싱글 플레이 게임 로직 단위 테스트"""

    def setUp(self):
        self.game = UpDownGame(nickname="Tester", max_attempts=7)
        self.game.target_number = 50

    def test_initial_state(self):
        self.assertEqual(self.game.nickname, "Tester")
        self.assertEqual(self.game.max_attempts, 7)
        self.assertEqual(self.game.attempts, 0)
        self.assertEqual(self.game.target_number, 50)
        self.assertFalse(self.game.is_over)

    def test_invalid_input(self):
        res1 = self.game.guess(0)
        self.assertEqual(res1["type"], "ERROR")
        self.assertEqual(self.game.attempts, 0)

        res2 = self.game.guess(101)
        self.assertEqual(res2["type"], "ERROR")
        self.assertEqual(self.game.attempts, 0)

    def test_up_down_judgement(self):
        res_up = self.game.guess(30)
        self.assertEqual(res_up["status"], "UP")
        self.assertEqual(res_up["attempts_used"], 1)

        res_down = self.game.guess(70)
        self.assertEqual(res_down["status"], "DOWN")
        self.assertEqual(res_down["attempts_used"], 2)

    def test_correct_and_bonus(self):
        win_res = self.game.guess(50)
        self.assertEqual(win_res["status"], "CORRECT")
        self.assertEqual(win_res["bonus_score"], 200)
        self.assertEqual(win_res["round_score"], 300)


class TestTwoPlayerGameRoom(unittest.TestCase):
    """2인 대결 룸 로직 단위 테스트"""

    def setUp(self):
        self.room = TwoPlayerGameRoom("Room_Test", "Player1", "Player2")
        self.room.target_number = 70

    def test_turn_enforcement_and_switching(self):
        """턴 검증 및 오답 시 상대방으로 턴 전환 검증"""
        self.assertEqual(self.room.current_turn, "Player1")

        # Player2가 먼저 추측 시도 -> 턴 위반 에러
        err_res = self.room.guess("Player2", 50)
        self.assertEqual(err_res["type"], "ERROR")

        # Player1이 정상 추측 -> UP 판정 및 Player2로 턴 전환
        guess_res = self.room.guess("Player1", 50)
        self.assertEqual(guess_res["status"], "UP")
        self.assertEqual(guess_res["current_turn"], "Player2")
        self.assertEqual(self.room.current_turn, "Player2")

    def test_win_and_scoring(self):
        """정답 시 승리 및 보너스 점수 획득 검증"""
        # Player1: 50 -> UP, 턴 Player2로 전환
        self.room.guess("Player1", 50)
        # Player2: 70 -> 정답!
        win_res = self.room.guess("Player2", 70)
        self.assertEqual(win_res["status"], "CORRECT")
        self.assertEqual(win_res["guesser"], "Player2")
        self.assertTrue(win_res["round_over"])
        self.assertEqual(self.room.scores["Player2"], 300)  # 2턴 만에 정답이므로 300점
        self.assertEqual(self.room.scores["Player1"], 0)

    def test_restart_voting(self):
        """두 플레이어 모두 동의 시 재시작 검증"""
        v1, _ = self.room.vote_restart("Player1")
        self.assertFalse(v1)  # 1명만 동의

        v2, _ = self.room.vote_restart("Player2")
        self.assertTrue(v2)  # 2명 모두 동의 -> 새 라운드 시작
        self.assertEqual(self.room.round_number, 2)


class TestTwoPlayerSocketServerIntegration(unittest.TestCase):
    """실제 소켓 서버를 통한 2인 매칭, 실시간 채팅, 추측 통합 테스트"""

    @classmethod
    def setUpClass(cls):
        cls.port = 29999
        cls.server = UpDownServer(host="127.0.0.1", port=cls.port)
        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_two_players_matching_and_chat(self):
        """2명 접속 -> 자동 매칭 -> 실시간 채팅(심리전) 송수신 검증"""
        # 플레이어 1 접속
        s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s1.connect(("127.0.0.1", self.port))
        stream1 = MessageStream(s1)
        stream1.send({"type": "LOGIN", "nickname": "Player1"})

        # Player1은 대기 메시지 수신
        wait_msg = stream1.recv()
        self.assertEqual(wait_msg.get("type"), "WAITING")

        # 플레이어 2 접속
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.connect(("127.0.0.1", self.port))
        stream2 = MessageStream(s2)
        stream2.send({"type": "LOGIN", "nickname": "Player2"})

        # 두 플레이어 모두 MATCH_FOUND 수신
        match1 = stream1.recv()
        match2 = stream2.recv()
        self.assertEqual(match1.get("type"), "MATCH_FOUND")
        self.assertEqual(match2.get("type"), "MATCH_FOUND")
        self.assertEqual(match1.get("opponent"), "Player2")
        self.assertEqual(match2.get("opponent"), "Player1")

        # 심리전 채팅 테스트: Player1이 "ㅋㅋㅋㅋㅋㅋ" 전송
        stream1.send({"type": "CHAT", "message": "ㅋㅋㅋㅋㅋㅋ"})
        chat_for_p1 = stream1.recv()
        chat_for_p2 = stream2.recv()

        self.assertEqual(chat_for_p1.get("sender"), "Player1")
        self.assertEqual(chat_for_p1.get("message"), "ㅋㅋㅋㅋㅋㅋ")
        self.assertEqual(chat_for_p2.get("sender"), "Player1")
        self.assertEqual(chat_for_p2.get("message"), "ㅋㅋㅋㅋㅋㅋ")

        # Player2가 "뭘 웃어?" 전송
        stream2.send({"type": "CHAT", "message": "뭘 웃어?"})
        chat_reply_p1 = stream1.recv()
        chat_reply_p2 = stream2.recv()

        self.assertEqual(chat_reply_p1.get("sender"), "Player2")
        self.assertEqual(chat_reply_p1.get("message"), "뭘 웃어?")
        self.assertEqual(chat_reply_p2.get("sender"), "Player2")
        self.assertEqual(chat_reply_p2.get("message"), "뭘 웃어?")

        stream1.close()
        stream2.close()


if __name__ == "__main__":
    unittest.main()
