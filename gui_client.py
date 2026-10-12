"""
gui_client.py - 1~100 UP/DOWN 2인 대결 및 실시간 채팅 GUI 클라이언트
(tkinter 기반 모던 다크 테마 UI)
"""
import sys
import socket
import threading
import argparse
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from protocol import MessageStream

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class UpDownGUIClient:
    # 모던 테마 색상 정의
    BG_COLOR = "#181825"
    CARD_BG = "#1e1e2e"
    TEXT_COLOR = "#cdd6f4"
    ACCENT_COLOR = "#89b4fa"
    MY_CHAT_COLOR = "#a6e3a1"
    OPP_CHAT_COLOR = "#f38ba8"
    SYS_COLOR = "#fab387"
    INPUT_BG = "#313244"
    BUTTON_BG = "#b4befe"
    BUTTON_FG = "#11111b"

    def __init__(self, host: str = "127.0.0.1", port: int = 9999, default_nick: str = "Player", pos_x: int = 100, pos_y: int = 100, quick_connect: bool = False):
        self.host = host
        self.port = port
        self.nickname = default_nick
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.quick_connect = quick_connect

        self.stream = None
        self.is_connected = False
        self.is_my_turn = False
        self.opponent_name = "상대방"
        self.my_score = 0
        self.opp_score = 0
        self.current_round = 1

        self.min_range = 1
        self.max_range = 100

        self.root = tk.Tk()
        self.setup_ui()

    def setup_ui(self):
        self.root.title("🎯 UP & DOWN 2인 심리전 미니 게임")
        self.root.geometry(f"780x640+{self.pos_x}+{self.pos_y}")
        self.root.minsize(720, 580)
        self.root.configure(bg=self.BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 1. 상단 헤더 프레임
        header_frame = tk.Frame(self.root, bg=self.CARD_BG, pady=10, padx=15)
        header_frame.pack(fill=tk.X, padx=12, pady=(10, 6))

        self.title_label = tk.Label(
            header_frame,
            text="🎯 UP & DOWN 2인 심리전 대결",
            font=("Malgun Gothic", 15, "bold"),
            bg=self.CARD_BG,
            fg=self.ACCENT_COLOR
        )
        self.title_label.pack(side=tk.LEFT)

        self.score_label = tk.Label(
            header_frame,
            text=f"{self.nickname} (0점)  VS  대기 중... (0점)",
            font=("Malgun Gothic", 12, "bold"),
            bg=self.CARD_BG,
            fg=self.TEXT_COLOR
        )
        self.score_label.pack(side=tk.RIGHT)

        # 2. 턴 및 상태 배너 프레임
        self.status_banner = tk.Label(
            self.root,
            text="상태: 서버에 연결 중...",
            font=("Malgun Gothic", 11, "bold"),
            bg="#45475a",
            fg="#ffffff",
            pady=6
        )
        self.status_banner.pack(fill=tk.X, padx=12, pady=(0, 8))

        # 3. 메인 콘텐츠 (좌: 게임판 / 우: 실시간 채팅)
        main_content = tk.Frame(self.root, bg=self.BG_COLOR)
        main_content.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # 3-1. 좌측: 게임 보드
        game_frame = tk.LabelFrame(
            main_content,
            text=" 🎲 게임 진행 & 판정 힌트 ",
            font=("Malgun Gothic", 11, "bold"),
            bg=self.CARD_BG,
            fg=self.ACCENT_COLOR,
            padx=10,
            pady=10
        )
        game_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # 범위 힌트 라벨
        self.range_hint_label = tk.Label(
            game_frame,
            text="🎯 정답 추측 범위: 1 ~ 100",
            font=("Malgun Gothic", 12, "bold"),
            bg=self.INPUT_BG,
            fg="#f9e2af",
            pady=8
        )
        self.range_hint_label.pack(fill=tk.X, pady=(0, 8))

        # 게임 진행 히스토리 뷰
        self.game_log = scrolledtext.ScrolledText(
            game_frame,
            font=("Consolas", 10),
            bg=self.INPUT_BG,
            fg=self.TEXT_COLOR,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.game_log.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 추측 입력 영역
        guess_input_frame = tk.Frame(game_frame, bg=self.CARD_BG)
        guess_input_frame.pack(fill=tk.X)

        self.guess_entry = tk.Entry(
            guess_input_frame,
            font=("Malgun Gothic", 12),
            bg=self.INPUT_BG,
            fg=self.TEXT_COLOR,
            insertbackground="white",
            state=tk.DISABLED
        )
        self.guess_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.guess_entry.bind("<Return>", lambda event: self.send_guess())

        self.guess_btn = tk.Button(
            guess_input_frame,
            text="추측하기 (Guess)",
            font=("Malgun Gothic", 10, "bold"),
            bg=self.BUTTON_BG,
            fg=self.BUTTON_FG,
            command=self.send_guess,
            state=tk.DISABLED,
            cursor="hand2",
            padx=8
        )
        self.guess_btn.pack(side=tk.RIGHT)

        # 3-2. 우측: 실시간 심리전 채팅창
        chat_frame = tk.LabelFrame(
            main_content,
            text=" 💬 실시간 심리전 채팅 ",
            font=("Malgun Gothic", 11, "bold"),
            bg=self.CARD_BG,
            fg=self.ACCENT_COLOR,
            padx=10,
            pady=10
        )
        chat_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        self.chat_view = scrolledtext.ScrolledText(
            chat_frame,
            font=("Malgun Gothic", 10),
            bg=self.INPUT_BG,
            fg=self.TEXT_COLOR,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.chat_view.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 텍스트 태그 설정 (색상 강조)
        self.chat_view.tag_config("my_chat", foreground=self.MY_CHAT_COLOR, font=("Malgun Gothic", 10, "bold"))
        self.chat_view.tag_config("opp_chat", foreground=self.OPP_CHAT_COLOR, font=("Malgun Gothic", 10, "bold"))
        self.chat_view.tag_config("sys_chat", foreground=self.SYS_COLOR, font=("Malgun Gothic", 9, "italic"))

        # 채팅 입력 프레임
        chat_input_frame = tk.Frame(chat_frame, bg=self.CARD_BG)
        chat_input_frame.pack(fill=tk.X)

        self.chat_entry = tk.Entry(
            chat_input_frame,
            font=("Malgun Gothic", 11),
            bg=self.INPUT_BG,
            fg=self.TEXT_COLOR,
            insertbackground="white"
        )
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.chat_entry.bind("<Return>", lambda event: self.send_chat())

        self.chat_btn = tk.Button(
            chat_input_frame,
            text="전송",
            font=("Malgun Gothic", 10, "bold"),
            bg=self.BUTTON_BG,
            fg=self.BUTTON_FG,
            command=self.send_chat,
            cursor="hand2",
            padx=12
        )
        self.chat_btn.pack(side=tk.RIGHT)

        # 4. 하단 유틸리티 바 (재시작 버튼 및 정보)
        bottom_frame = tk.Frame(self.root, bg=self.CARD_BG, pady=8, padx=15)
        bottom_frame.pack(fill=tk.X, padx=12, pady=(6, 10))

        self.info_lbl = tk.Label(
            bottom_frame,
            text="💡 팁: 번갈아가며 추측하고, 언제든 채팅으로 심리전을 걸어보세요!",
            font=("Malgun Gothic", 9),
            bg=self.CARD_BG,
            fg="#a6adc8"
        )
        self.info_lbl.pack(side=tk.LEFT)

        self.restart_btn = tk.Button(
            bottom_frame,
            text="🔄 다시하기 (Restart)",
            font=("Malgun Gothic", 10, "bold"),
            bg="#a6e3a1",
            fg="#11111b",
            state=tk.DISABLED,
            command=self.send_restart,
            cursor="hand2",
            padx=10
        )
        self.restart_btn.pack(side=tk.RIGHT)

    def log_game(self, text: str):
        """게임 히스토리 추가"""
        self.game_log.config(state=tk.NORMAL)
        self.game_log.insert(tk.END, text + "\n")
        self.game_log.see(tk.END)
        self.game_log.config(state=tk.DISABLED)

    def append_chat(self, sender: str, msg: str, tag: str = "sys_chat"):
        """채팅창에 메시지 추가"""
        self.chat_view.config(state=tk.NORMAL)
        if tag == "sys_chat":
            self.chat_view.insert(tk.END, f"📢 [시스템] {msg}\n", tag)
        else:
            self.chat_view.insert(tk.END, f"{sender} : {msg}\n", tag)
        self.chat_view.see(tk.END)
        self.chat_view.config(state=tk.DISABLED)

    def update_status(self, is_my_turn: bool, custom_msg: str = None):
        """턴 상태 및 입력창 활성화 업데이트"""
        self.is_my_turn = is_my_turn
        if custom_msg:
            self.status_banner.config(text=custom_msg, bg="#45475a")
            self.guess_entry.config(state=tk.DISABLED)
            self.guess_btn.config(state=tk.NORMAL, bg="#585b70", fg="#cdd6f4", text="⏳ 대기 중")
        elif is_my_turn:
            self.status_banner.config(text="🟢 [내 차례] 1~100 숫자를 입력하고 추측하세요!", bg="#2e7d32")
            self.guess_entry.config(state=tk.NORMAL)
            self.guess_btn.config(state=tk.NORMAL, bg="#a6e3a1", fg="#11111b", text="🎯 추측하기 (내 차례)")
            self.guess_entry.focus_set()
        else:
            self.status_banner.config(text=f"⏳ [{self.opponent_name}]님의 턴입니다. (상대방 창에서 진행 중)", bg="#c678dd")
            self.guess_entry.config(state=tk.DISABLED)
            self.guess_btn.config(state=tk.NORMAL, bg="#45475a", fg="#cdd6f4", text=f"⏳ {self.opponent_name} 턴 진행 중")

    def send_chat(self):
        """채팅 메시지 전송"""
        text = self.chat_entry.get().strip()
        if not text or not self.stream:
            return
        self.chat_entry.delete(0, tk.END)
        try:
            self.stream.send({"type": "CHAT", "message": text})
        except Exception:
            self.append_chat("시스템", "메시지 전송에 실패했습니다.", "sys_chat")

    def send_guess(self):
        """숫자 추측 전송"""
        if not self.is_connected or not self.stream:
            messagebox.showwarning("연결 확인", "아직 서버에 연결되지 않았습니다.")
            return

        if not self.is_my_turn:
            messagebox.showinfo(
                "차례 안내",
                f"지금은 상대방 [{self.opponent_name}]님의 차례(턴)입니다!\n\n"
                f"상대방 창([{self.opponent_name}])에서 숫자를 먼저 추측해야 합니다.\n\n"
                "💡 혹시 화면에 창이 하나만 보인다면, 두 창이 완전히 겹쳐져 있는 것입니다.\n"
                "현재 창 상단을 마우스로 드래그해서 옆으로 치우면 밑에 있는 상대방 창이 보입니다!"
            )
            return

        val = self.guess_entry.get().strip()
        if not val:
            messagebox.showwarning("입력 필요", "추측할 1~100 사이의 숫자를 먼저 입력창에 적어주세요!")
            self.guess_entry.focus_set()
            return

        try:
            num = int(val)
        except ValueError:
            messagebox.showwarning("입력 오류", "1부터 100 사이의 숫자를 입력해주세요!")
            self.guess_entry.delete(0, tk.END)
            return

        if num < 1 or num > 100:
            messagebox.showwarning("범위 초과", "1부터 100 사이의 범위 내 숫자여야 합니다!")
            self.guess_entry.delete(0, tk.END)
            return

        self.guess_entry.delete(0, tk.END)
        try:
            self.stream.send({"type": "GUESS", "number": num})
        except Exception:
            messagebox.showerror("오류", "서버 전송 중 문제가 발생했습니다.")

    def send_restart(self):
        """재시작 요청 전송"""
        if self.stream:
            try:
                self.stream.send({"type": "RESTART"})
                self.restart_btn.config(state=tk.DISABLED)
                self.append_chat("시스템", "재시작을 요청했습니다. 상대방 응답 대기 중...", "sys_chat")
            except Exception:
                pass

    def start_network(self):
        """백그라운드 네트워크 수신 스레드 가동"""
        thread = threading.Thread(target=self.network_loop, daemon=True)
        thread.start()

    def network_loop(self):
        """서버 연결 및 패킷 수신 루프"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(6.0)
        try:
            sock.connect((self.host, self.port))
            sock.settimeout(None)
            self.stream = MessageStream(sock)
            self.is_connected = True

            # LOGIN 전송
            self.stream.send({"type": "LOGIN", "nickname": self.nickname})

            while self.is_connected:
                msg = self.stream.recv()
                if msg is None:
                    break
                self.root.after(0, self.handle_server_message, msg)

        except (ConnectionRefusedError, socket.timeout):
            self.root.after(0, lambda: messagebox.showerror(
                "서버 접속 불가",
                f"서버({self.host}:{self.port})에 연결할 수 없습니다.\nserver.py 가 실행 중인지 확인해주세요!"
            ))
            self.root.after(0, self.root.destroy)
        except Exception as e:
            self.root.after(0, lambda: self.append_chat("시스템", f"오류 발생: {e}", "sys_chat"))
        finally:
            self.is_connected = False
            self.root.after(0, lambda: self.update_status(False, "서버와의 연결이 종료되었습니다."))

    def handle_server_message(self, msg: dict):
        """서버로부터 온 메시지 처리 (Tkinter 메인 스레드에서 실행)"""
        m_type = msg.get("type")

        if m_type == "WAITING":
            self.update_status(False, "⏳ [대기 중 1/2] 2번째 플레이어가 접속하면 게임판이 활성화됩니다!")
            self.log_game("📌 상대 플레이어의 접속을 기다리는 중입니다... (1/2)")
            self.log_game("💡 2인 대결 게임입니다. 2번째 창이 접속하면 숫자 입력창이 열립니다.")

        elif m_type == "MATCH_FOUND":
            self.nickname = msg.get("you", self.nickname)
            self.opponent_name = msg.get("opponent", "상대방")
            self.current_round = msg.get("round", 1)
            turn = msg.get("current_turn")

            self.score_label.config(text=f"{self.nickname} ({self.my_score}점)  VS  {self.opponent_name} ({self.opp_score}점)")
            self.log_game(f"🎉 2인 매칭 완료! 상대방: [{self.opponent_name}]")
            self.log_game(f"🎲 [라운드 {self.current_round}] 1부터 100 사이의 숫자를 맞춰보세요!")
            self.append_chat("시스템", f"[{self.opponent_name}]님과 매칭되었습니다! 심리전을 시작하세요!", "sys_chat")

            self.min_range = 1
            self.max_range = 100
            self.range_hint_label.config(text=f"🎯 정답 추측 범위: {self.min_range} ~ {self.max_range}")
            self.restart_btn.config(state=tk.DISABLED)
            self.update_status(turn == self.nickname)

        elif m_type == "CHAT":
            sender = msg.get("sender")
            text = msg.get("message")
            if sender == self.nickname:
                self.append_chat(f"나({sender})", text, "my_chat")
            elif sender == "시스템":
                self.append_chat(sender, text, "sys_chat")
            else:
                self.append_chat(sender, text, "opp_chat")

        elif m_type == "GUESS_RESULT":
            guesser = msg.get("guesser")
            num = msg.get("number")
            status = msg.get("status")
            hint_msg = msg.get("message")
            scores = msg.get("scores", {})
            round_over = msg.get("round_over", False)
            next_turn = msg.get("current_turn")

            self.my_score = scores.get(self.nickname, self.my_score)
            self.opp_score = scores.get(self.opponent_name, self.opp_score)
            self.score_label.config(text=f"{self.nickname} ({self.my_score}점)  VS  {self.opponent_name} ({self.opp_score}점)")

            if status == "UP":
                self.min_range = max(self.min_range, num + 1)
                self.log_game(f"🔺 {hint_msg}")
            elif status == "DOWN":
                self.max_range = min(self.max_range, num - 1)
                self.log_game(f"🔻 {hint_msg}")
            elif status == "CORRECT":
                self.log_game(f"\n{'★' * 40}\n{hint_msg}\n{'★' * 40}\n")
            elif status == "GAME_OVER":
                self.log_game(f"\n{'!' * 40}\n{hint_msg}\n{'!' * 40}\n")

            self.range_hint_label.config(text=f"🎯 정답 추측 범위: {self.min_range} ~ {self.max_range}")

            # 채팅창에도 판정 결과 및 힌트 공유
            self.append_chat("시스템", hint_msg, "sys_chat")

            if round_over:
                self.update_status(False, f"🏆 라운드 종료! (정답: {msg.get('target')})")
                self.restart_btn.config(state=tk.NORMAL)
                self.append_chat("시스템", f"🏆 라운드 종료! 정답은 [{msg.get('target')}]였습니다.", "sys_chat")
            else:
                self.update_status(next_turn == self.nickname)
                self.append_chat("시스템", f"👉 다음 차례: [{next_turn}]님의 턴입니다.", "sys_chat")

        elif m_type == "ROUND_START":
            self.current_round = msg.get("round", self.current_round + 1)
            turn = msg.get("current_turn")
            self.min_range = 1
            self.max_range = 100
            self.range_hint_label.config(text=f"🎯 정답 추측 범위: {self.min_range} ~ {self.max_range}")
            self.log_game(f"\n================ [라운드 {self.current_round} 시작] ================")
            self.restart_btn.config(state=tk.DISABLED)
            self.update_status(turn == self.nickname)

        elif m_type == "OPPONENT_LEFT":
            self.append_chat("시스템", msg.get("message", "상대방이 퇴장했습니다."), "sys_chat")
            self.update_status(False, "❌ 상대방이 퇴장했습니다.")
            self.guess_entry.config(state=tk.DISABLED)
            self.guess_btn.config(state=tk.DISABLED)
            self.restart_btn.config(state=tk.DISABLED)
            messagebox.showinfo("상대방 퇴장", msg.get("message"))

        elif m_type == "ERROR":
            messagebox.showwarning("경고", msg.get("message"))

    def show_connect_dialog(self):
        """서버 IP 및 닉네임 설정을 위한 모달 다이얼로그"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🌐 서버 접속 설정")
        dialog.geometry("380x280")
        dialog.resizable(False, False)
        dialog.configure(bg=self.CARD_BG)
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.pos_x + 200
        y = self.pos_y + 160
        dialog.geometry(f"+{max(10, x)}+{max(10, y)}")

        title_lbl = tk.Label(
            dialog,
            text="🎮 UP & DOWN 2인 대결 서버 접속",
            font=("Malgun Gothic", 12, "bold"),
            bg=self.CARD_BG,
            fg=self.ACCENT_COLOR
        )
        title_lbl.pack(pady=(15, 10))

        form_frame = tk.Frame(dialog, bg=self.CARD_BG)
        form_frame.pack(fill=tk.X, padx=30)

        # 1. 서버 IP
        tk.Label(form_frame, text="서버 IP:", font=("Malgun Gothic", 10, "bold"), bg=self.CARD_BG, fg=self.TEXT_COLOR).grid(row=0, column=0, sticky="w", pady=5)
        ip_entry = tk.Entry(form_frame, font=("Malgun Gothic", 10), bg=self.INPUT_BG, fg=self.TEXT_COLOR, insertbackground="white")
        ip_entry.insert(0, self.host)
        ip_entry.grid(row=0, column=1, sticky="ew", pady=5, padx=(10, 0))

        # 2. 포트
        tk.Label(form_frame, text="포트 번호:", font=("Malgun Gothic", 10, "bold"), bg=self.CARD_BG, fg=self.TEXT_COLOR).grid(row=1, column=0, sticky="w", pady=5)
        port_entry = tk.Entry(form_frame, font=("Malgun Gothic", 10), bg=self.INPUT_BG, fg=self.TEXT_COLOR, insertbackground="white")
        port_entry.insert(0, str(self.port))
        port_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 0))

        # 3. 닉네임
        tk.Label(form_frame, text="내 닉네임:", font=("Malgun Gothic", 10, "bold"), bg=self.CARD_BG, fg=self.TEXT_COLOR).grid(row=2, column=0, sticky="w", pady=5)
        nick_entry = tk.Entry(form_frame, font=("Malgun Gothic", 10), bg=self.INPUT_BG, fg=self.TEXT_COLOR, insertbackground="white")
        nick_entry.insert(0, self.nickname)
        nick_entry.grid(row=2, column=1, sticky="ew", pady=5, padx=(10, 0))

        form_frame.columnconfigure(1, weight=1)

        def on_connect_btn():
            ip_val = ip_entry.get().strip()
            port_val = port_entry.get().strip()
            nick_val = nick_entry.get().strip() or "Player"

            if not ip_val:
                messagebox.showwarning("입력 필요", "서버 IP를 입력해주세요!")
                return
            try:
                p_val = int(port_val)
            except ValueError:
                messagebox.showwarning("입력 오류", "포트 번호는 숫자여야 합니다.")
                return

            self.host = ip_val
            self.port = p_val
            self.nickname = nick_val
            self.score_label.config(text=f"{self.nickname} (0점)  VS  대기 중... (0점)")
            dialog.destroy()
            self.start_network()

        dialog.protocol("WM_DELETE_WINDOW", lambda: self.root.destroy())

        btn = tk.Button(
            dialog,
            text="🚀 게임 서버 접속하기",
            font=("Malgun Gothic", 11, "bold"),
            bg="#a6e3a1",
            fg="#11111b",
            cursor="hand2",
            command=on_connect_btn
        )
        btn.pack(fill=tk.X, padx=30, pady=(20, 10))
        nick_entry.bind("<Return>", lambda e: on_connect_btn())
        ip_entry.bind("<Return>", lambda e: on_connect_btn())

    def on_closing(self):
        """창 종료 이벤트"""
        self.is_connected = False
        if self.stream:
            try:
                self.stream.send({"type": "QUIT"})
            except Exception:
                pass
            self.stream.close()
        self.root.destroy()

    def run(self):
        if self.quick_connect:
            self.start_network()
        else:
            self.root.after(100, self.show_connect_dialog)
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="UP/DOWN 2인 심리전 GUI 클라이언트")
    parser.add_argument("--host", default="127.0.0.1", help="서버 IP")
    parser.add_argument("--port", type=int, default=9999, help="서버 포트")
    parser.add_argument("--nick", default="Player1", help="플레이어 닉네임")
    parser.add_argument("--x", type=int, default=60, help="창 초기 X 좌표")
    parser.add_argument("--y", type=int, default=60, help="창 초기 Y 좌표")
    parser.add_argument("--quick", action="store_true", help="접속 다이얼로그 생략하고 바로 접속")
    args = parser.parse_args()

    client = UpDownGUIClient(
        host=args.host,
        port=args.port,
        default_nick=args.nick,
        pos_x=args.x,
        pos_y=args.y,
        quick_connect=args.quick
    )
    client.run()


if __name__ == "__main__":
    main()
