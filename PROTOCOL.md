# TCP 소켓 기반 UP/DOWN 2인 미니 게임 프로토콜 및 메시지 규칙 설계

## 1. 개요
본 문서는 Python의 TCP 소켓(`socket` 모듈)을 이용한 **2인 대결 숫자 맞추기(UP/DOWN) & 실시간 채팅 심리전 게임**의 통신 규약(Protocol) 및 메시지 구조를 정의합니다.

- **전송 계층 프로토콜**: TCP (IPv4: AF_INET, SOCK_STREAM)
- **기본 접속 주소**: `127.0.0.1` (localhost)
- **기본 포트**: `9999`
- **인코딩**: UTF-8
- **메시지 프레이밍 (Framing)**: JSON 객체 + 개행 문자(`\n`, Newline-delimited JSON)
  - 모든 패킷 끝에 `\n` 구분자를 두어 TCP 스트림 버퍼링 및 패킷 분할/병합 문제를 안전하게 해결합니다.

---

## 2. 메시지 구조 및 규칙

### 2.1 클라이언트 → 서버 메시지 (Client to Server)

| 메시지 타입 (`type`) | 필드 구성 | 설명 |
| :--- | :--- | :--- |
| `LOGIN` | `{"type": "LOGIN", "nickname": "홍길동"}` | 닉네임 등록 및 게임 매칭 큐 등록 |
| `CHAT` | `{"type": "CHAT", "message": "ㅋㅋㅋㅋㅋㅋ"}` | 상대방과의 실시간 심리전 채팅 전송 (언제든 전송 가능) |
| `GUESS` | `{"type": "GUESS", "number": 50}` | 자신의 턴에 1~100 사이 숫자 추측 전송 |
| `RESTART` | `{"type": "RESTART"}` | 라운드 종료 후 재시작 요청 |
| `QUIT` | `{"type": "QUIT"}` | 접속 종료 |

---

### 2.2 서버 → 클라이언트 메시지 (Server to Client)

| 메시지 타입 (`type`) | 필드 구성 | 설명 |
| :--- | :--- | :--- |
| `WAITING` | `message` | 상대 플레이어 대기 알림 ("상대방을 기다리는 중입니다... 1/2") |
| `MATCH_FOUND` | `room_id`, `opponent`, `current_turn`, `round`, `message` | 2인 매칭 완료 및 게임 시작 알림 |
| `CHAT` | `sender`, `message` | 수신된 채팅 메시지 브로드캐스트 |
| `GUESS_RESULT` | `guesser`, `number`, `status`, `message`, `current_turn`, `scores`, `target`, `round_over`, `attempts_used`, `attempts_left` | 추측 결과(UP/DOWN/CORRECT/GAME_OVER) 및 턴 변경 알림 |
| `ROUND_START` | `round`, `current_turn`, `message` | 새 라운드 시작 알림 |
| `OPPONENT_LEFT` | `message` | 상대방의 연결 종료 통보 |
| `ERROR` | `message` | 유효하지 않은 입력 또는 턴 위반 경고 |

---

## 3. 2인 대결 및 보너스 점수 규칙

1. **2인 턴제 대결**:
   - 서버가 1 ~ 100 사이의 무작위 숫자를 선정합니다.
   - 두 플레이어가 번갈아가며(Turn-based) 숫자를 추측합니다.
   - 추측 결과(UP/DOWN)는 두 플레이어 모두에게 실시간 공유되어 힌트가 됩니다.
2. **실시간 심리전 채팅**:
   - 턴과 상관없이 언제든지 실시간으로 채팅을 주고받으며 심리전을 펼칠 수 있습니다. (예: "Player1 : ㅋㅋㅋㅋㅋㅋ", "Player2 : 뭘 웃어?")
3. **보너스 점수 시스템**:
   - ⚡ **빠른 정답 보너스 (총 4턴 이내 정답)**: 300점
   - ✨ **우수 정답 보너스 (총 5~8턴 이내 정답)**: 150점
   - 👍 **일반 정답 (총 9턴 이후 정답)**: 100점
   - 먼저 정답을 맞춘 플레이어가 해당 라운드의 점수를 획득합니다.
4. **재시작**:
   - 라운드 종료 후 두 플레이어가 재시작을 누르면 누적 점수를 유지한 채 새 라운드가 시작됩니다.
