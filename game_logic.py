"""
game_logic.py - 1~100 UP/DOWN 숫자 맞추기 게임 핵심 로직 모듈
(싱글 플레이 및 2인 대결 멀티플레이어 룸 지원)
"""
import random
from typing import Optional, Dict, Any, Tuple, List


class UpDownGame:
    """
    1인 싱글 모드 UP/DOWN 세션 로직
    """

    MIN_NUMBER = 1
    MAX_NUMBER = 100
    DEFAULT_MAX_ATTEMPTS = 7

    def __init__(self, nickname: str = "플레이어", max_attempts: int = DEFAULT_MAX_ATTEMPTS):
        self.nickname = nickname
        self.max_attempts = max_attempts
        self.total_score = 0
        self.rounds_played = 0
        self.rounds_won = 0

        self.target_number = 0
        self.attempts = 0
        self.is_over = False
        self.is_won = False
        self.round_history = []
        self.start_new_round()

    def start_new_round(self, forced_target: Optional[int] = None) -> int:
        self.rounds_played += 1
        self.attempts = 0
        self.is_over = False
        self.is_won = False
        self.round_history = []

        if forced_target is not None:
            self.target_number = forced_target
        else:
            self.target_number = random.randint(self.MIN_NUMBER, self.MAX_NUMBER)
        return self.target_number

    def calculate_score(self, attempts_used: int) -> Tuple[int, int]:
        base_score = 100
        if attempts_used <= 3:
            bonus = 200
        elif attempts_used <= 5:
            bonus = 50
        else:
            bonus = 0
        return bonus, base_score + bonus

    def guess(self, number: int) -> Dict[str, Any]:
        if self.is_over:
            return {"type": "ERROR", "message": "현재 라운드가 이미 종료되었습니다."}

        if not isinstance(number, int) or number < self.MIN_NUMBER or number > self.MAX_NUMBER:
            return {"type": "ERROR", "message": f"{self.MIN_NUMBER}부터 {self.MAX_NUMBER} 사이의 유효한 정수를 입력해주세요."}

        self.attempts += 1
        self.round_history.append(number)
        attempts_left = self.max_attempts - self.attempts

        if number == self.target_number:
            self.is_over = True
            self.is_won = True
            self.rounds_won += 1
            bonus, round_score = self.calculate_score(self.attempts)
            self.total_score += round_score
            return {
                "type": "RESULT",
                "status": "CORRECT",
                "message": f"🎉 정답입니다! 숫자는 {self.target_number}였습니다!",
                "attempts_used": self.attempts,
                "attempts_left": attempts_left,
                "bonus_score": bonus,
                "round_score": round_score,
                "total_score": self.total_score,
                "target": self.target_number
            }

        if attempts_left <= 0:
            self.is_over = True
            self.is_won = False
            return {
                "type": "RESULT",
                "status": "GAME_OVER",
                "message": f"😢 기회를 모두 소진했습니다! 정답은 [{self.target_number}]였습니다.",
                "attempts_used": self.attempts,
                "attempts_left": 0,
                "bonus_score": 0,
                "round_score": 0,
                "total_score": self.total_score,
                "target": self.target_number
            }

        status = "UP" if number < self.target_number else "DOWN"
        msg = f"🔺 UP! ({number}보다 큼)" if status == "UP" else f"🔻 DOWN! ({number}보다 작음)"

        return {
            "type": "RESULT",
            "status": status,
            "message": msg,
            "attempts_used": self.attempts,
            "attempts_left": attempts_left,
            "bonus_score": 0,
            "round_score": 0,
            "total_score": self.total_score,
            "target": None
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            "nickname": self.nickname,
            "rounds_played": self.rounds_played,
            "rounds_won": self.rounds_won,
            "total_score": self.total_score
        }


class TwoPlayerGameRoom:
    """
    2인 대결 UP/DOWN 게임 룸 로직 클래스
    실시간 턴 교체, 보너스 점수 분배, 힌트 공유를 담당합니다.
    """

    MIN_NUMBER = 1
    MAX_NUMBER = 100
    TOTAL_MAX_ATTEMPTS = 12

    def __init__(self, room_id: str, p1_nick: str, p2_nick: str):
        self.room_id = room_id
        self.players = [p1_nick, p2_nick]
        self.scores = {p1_nick: 0, p2_nick: 0}
        self.round_number = 0
        self.target_number = 0
        self.current_turn = p1_nick
        self.attempts_used = 0
        self.is_over = False
        self.winner = None
        self.restart_votes = set()
        self.start_new_round()

    def start_new_round(self, forced_target: Optional[int] = None) -> int:
        self.round_number += 1
        self.attempts_used = 0
        self.is_over = False
        self.winner = None
        self.restart_votes.clear()
        # 라운드마다 선공 번갈아가기
        self.current_turn = self.players[(self.round_number - 1) % 2]

        if forced_target is not None:
            self.target_number = forced_target
        else:
            self.target_number = random.randint(self.MIN_NUMBER, self.MAX_NUMBER)
        return self.target_number

    def get_other_player(self, nick: str) -> str:
        return self.players[1] if nick == self.players[0] else self.players[0]

    def switch_turn(self):
        self.current_turn = self.get_other_player(self.current_turn)

    def calculate_bonus(self, turn_count: int) -> int:
        """
        턴 수에 따른 보너스 점수:
        - 1~4턴 내: 300점 (초특급 보너스)
        - 5~8턴 내: 150점 (우수 보너스)
        - 9턴 이상: 100점 (일반 정답)
        """
        if turn_count <= 4:
            return 300
        elif turn_count <= 8:
            return 150
        return 100

    def guess(self, player_nick: str, number: int) -> Dict[str, Any]:
        """추측 처리 및 판정 결과 생성"""
        if self.is_over:
            return {
                "type": "ERROR",
                "message": "이번 라운드가 이미 종료되었습니다. 재시작을 눌러주세요."
            }

        if player_nick != self.current_turn:
            return {
                "type": "ERROR",
                "message": f"지금은 [{self.current_turn}]님의 턴입니다. 차례를 기다려주세요!"
            }

        if not isinstance(number, int) or number < self.MIN_NUMBER or number > self.MAX_NUMBER:
            return {
                "type": "ERROR",
                "message": f"{self.MIN_NUMBER}부터 {self.MAX_NUMBER} 사이의 정수를 입력해주세요."
            }

        self.attempts_used += 1
        attempts_left = self.TOTAL_MAX_ATTEMPTS - self.attempts_used

        # 1. 정답인 경우
        if number == self.target_number:
            self.is_over = True
            self.winner = player_nick
            score = self.calculate_bonus(self.attempts_used)
            self.scores[player_nick] += score

            return {
                "type": "GUESS_RESULT",
                "guesser": player_nick,
                "number": number,
                "status": "CORRECT",
                "message": f"🎉 [{player_nick}]님이 정답({self.target_number})을 맞췄습니다! (+{score}점)",
                "current_turn": None,
                "scores": dict(self.scores),
                "target": self.target_number,
                "round_over": True,
                "attempts_used": self.attempts_used,
                "attempts_left": attempts_left,
                "round_score": score
            }

        # 2. 기회 소진 (무승부)
        if attempts_left <= 0:
            self.is_over = True
            return {
                "type": "GUESS_RESULT",
                "guesser": player_nick,
                "number": number,
                "status": "GAME_OVER",
                "message": f"😢 두 플레이어 모두 기회를 소진했습니다! 정답은 [{self.target_number}]였습니다.",
                "current_turn": None,
                "scores": dict(self.scores),
                "target": self.target_number,
                "round_over": True,
                "attempts_used": self.attempts_used,
                "attempts_left": 0,
                "round_score": 0
            }

        # 3. UP / DOWN 판정 후 턴 교체
        status = "UP" if number < self.target_number else "DOWN"
        status_text = "더 큰 숫자(UP)" if status == "UP" else "더 작은 숫자(DOWN)"
        hint_msg = f"[{player_nick}]의 추측 {number} ➔ {status}! ({status_text})"

        self.switch_turn()

        return {
            "type": "GUESS_RESULT",
            "guesser": player_nick,
            "number": number,
            "status": status,
            "message": hint_msg,
            "current_turn": self.current_turn,
            "scores": dict(self.scores),
            "target": None,
            "round_over": False,
            "attempts_used": self.attempts_used,
            "attempts_left": attempts_left,
            "round_score": 0
        }

    def vote_restart(self, player_nick: str) -> Tuple[bool, str]:
        """재시작 투표 처리: 양쪽 모두 투표 시 새 라운드 시작"""
        self.restart_votes.add(player_nick)
        if len(self.restart_votes) >= 2:
            self.start_new_round()
            return True, "두 플레이어 모두 동의하여 새로운 라운드가 시작됩니다!"
        else:
            return False, f"[{player_nick}]님이 재시작을 요청했습니다. 상대방 동의를 기다리는 중입니다..."
