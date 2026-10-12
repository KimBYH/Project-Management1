"""
protocol.py - TCP 소켓 통신을 위한 메시지 인코딩/디코딩 및 버퍼 스트림 유틸리티
"""
import json
import socket
from typing import Optional, Dict, Any


class MessageStream:
    """
    개행 문자('\n')로 구분된 JSON 메시지를 송수신하는 스트림 래퍼 클래스입니다.
    TCP의 패킷 분할(Fragmentation) 및 결합(Coalescing) 문제를 버퍼링으로 안전하게 해결합니다.
    """

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self._buffer = b""

    def send(self, payload: Dict[str, Any]) -> None:
        """
        딕셔너리 데이터를 JSON으로 직렬화하고 끝에 개행 문자('\n')를 붙여 전송합니다.
        """
        json_str = json.dumps(payload, ensure_ascii=False)
        data = json_str.encode("utf-8") + b"\n"
        self.sock.sendall(data)

    def recv(self) -> Optional[Dict[str, Any]]:
        """
        스트림에서 개행 문자('\n')를 만날 때까지 수신하여 파싱된 JSON 딕셔너리를 반환합니다.
        연결이 정상 또는 비정상적으로 종료되면 None을 반환합니다.
        """
        while b"\n" not in self._buffer:
            try:
                chunk = self.sock.recv(4096)
            except (ConnectionResetError, ConnectionAbortedError, TimeoutError, OSError):
                return None

            if not chunk:
                # 상대방이 연결을 종료함 (EOF)
                return None
            self._buffer += chunk

        # 개행 문자를 기준으로 첫 번째 메시지 분리
        line, self._buffer = self._buffer.split(b"\n", 1)
        line = line.strip()
        if not line:
            return self.recv()

        try:
            return json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # 비정상 데이터 무시 후 다음 메시지 시도
            return {"type": "ERROR", "message": "유효하지 않은 메시지 형식입니다."}

    def close(self) -> None:
        """소켓을 안전하게 닫습니다."""
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.sock.close()
