"""정답 해시 (HMAC-SHA256).

평문 정답은 어디에도 저장하지 않는다. 비밀 키(secrets/hmac.key)로 만든 HMAC만 저장한다.
그냥 SHA-256을 쓰지 않고 비밀 키를 섞는 이유: 4지선다나 짧은 글자처럼 정답 후보가 적으면
해시만 보고 모든 후보를 대입해 정답을 알아낼 수 있다. 키가 없으면 그게 불가능하다.
"""
import hashlib
import hmac
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY_PATH = ROOT / "secrets" / "hmac.key"


def load_key(create: bool = False) -> bytes:
    if not KEY_PATH.exists():
        if not create:
            raise FileNotFoundError(f"{KEY_PATH} 가 없습니다. 먼저 문제를 생성하세요.")
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        KEY_PATH.write_text(secrets.token_hex(32) + "\n")
    return bytes.fromhex(KEY_PATH.read_text().strip())


def answer_hash(key: bytes, mission: str, q_no: int, answer: str) -> str:
    msg = f"{mission}|{q_no}|{answer}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def check(key: bytes, mission: str, q_no: int, answer: str, expected: str) -> bool:
    return hmac.compare_digest(answer_hash(key, mission, q_no, answer), expected)
