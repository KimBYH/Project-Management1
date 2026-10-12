"""
simulate_client.py - 2개 터미널 시뮬레이션을 위한 자동 클라이언트 동작 검증 스크립트
"""
import sys
import time
import socket
from protocol import MessageStream

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_simulation(host="127.0.0.1", port=9999):
    print("=" * 60)
    print("🤖 [시뮬레이션 클라이언트] 서버에 연결을 시도합니다...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    stream = MessageStream(sock)

    # 1. 닉네임 전송
    nickname = "철수(Player1)"
    print(f">> [보냄] LOGIN 닉네임: {nickname}")
    stream.send({"type": "LOGIN", "nickname": nickname})

    welcome = stream.recv()
    print(f"<< [받음] WELCOME: {welcome.get('message')}\n")

    # 라운드 1 시작
    round1 = stream.recv()
    print(f"<< [받음] ROUND_START: {round1.get('message')}")

    # 잘못된 입력 테스트 (150, -5)
    print(">> [보냄] GUESS 150 (잘못된 범위 테스트)")
    stream.send({"type": "GUESS", "number": 150})
    err_res = stream.recv()
    print(f"<< [받음] {err_res.get('message')}")

    # 이진 탐색으로 정답 찾기 시뮬레이션
    low = 1
    high = 100
    round_over = False

    while not round_over:
        mid = (low + high) // 2
        print(f">> [보냄] GUESS: {mid}")
        stream.send({"type": "GUESS", "number": mid})
        res = stream.recv()
        status = res.get("status")
        print(f"<< [받음] 판정: {status} | 메시지: {res.get('message')} | 사용 횟수: {res.get('attempts_used')}")

        if status == "CORRECT":
            print(f"🎉 정답 달성! 획득 점수: {res.get('round_score')}점 (보너스: {res.get('bonus_score')}점)")
            round_over = True
        elif status == "GAME_OVER":
            print("😢 기회 소진!")
            round_over = True
        elif status == "UP":
            low = mid + 1
        elif status == "DOWN":
            high = mid - 1

    # 재시작(Y) 테스트
    print("\n>> [보냄] RESTART: 'Y' (재시작 요청)")
    stream.send({"type": "RESTART", "decision": "Y"})

    round2 = stream.recv()
    print(f"<< [받음] ROUND_START: {round2.get('message')}")

    # 2라운드는 'QUIT'으로 종료 테스트
    print(">> [보냄] QUIT (게임 종료 요청)")
    stream.send({"type": "QUIT"})
    goodbye = stream.recv()
    print(f"<< [받음] GOODBYE: {goodbye.get('message')}")
    print(f"📊 최종 결과 요약: {goodbye.get('summary')}")

    stream.close()
    print("\n[✔] 시뮬레이션 클라이언트가 성공적으로 완료되었습니다!")


if __name__ == "__main__":
    run_simulation()
