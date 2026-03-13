"""Generate a realistic sample session log for demo purposes."""

import json
import uuid
from datetime import datetime, timedelta

SESSION_ID = "sample-demo-session-001"
BASE_TIME = datetime(2026, 3, 10, 14, 0, 0)


def ts(offset_sec: int) -> str:
    return (BASE_TIME + timedelta(seconds=offset_sec)).isoformat() + "Z"


def user_msg(parent_uuid, content, offset):
    uid = str(uuid.uuid4())
    return uid, json.dumps({
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "userType": "external",
        "cwd": "/home/user/project",
        "sessionId": SESSION_ID,
        "version": "2.2.0",
        "type": "user",
        "message": {"role": "user", "content": content},
        "uuid": uid,
        "timestamp": ts(offset),
    })


def assistant_msg(parent_uuid, content_items, usage, offset):
    uid = str(uuid.uuid4())
    return uid, json.dumps({
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "userType": "external",
        "cwd": "/home/user/project",
        "sessionId": SESSION_ID,
        "version": "2.2.0",
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": content_items,
            "usage": usage,
        },
        "uuid": uid,
        "timestamp": ts(offset),
    })


def tool_use(name, input_args):
    return {"type": "tool_use", "id": f"toolu_{uuid.uuid4().hex[:12]}", "name": name, "input": input_args}


def text_block(text):
    return {"type": "text", "text": text}


def usage(inp=10, out=100, cache_read=5000, cache_create=0):
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_create,
    }


def generate():
    lines = []
    t = 0

    # User asks to refactor auth module
    uid, line = user_msg(None, "auth 모듈을 리팩토링해줘. 세션 관리 로직을 분리하고 싶어.", t)
    lines.append(line)
    t += 5

    # Assistant reads the file
    aid, line = assistant_msg(uid, [
        text_block("auth 모듈을 확인하겠습니다."),
        tool_use("Read", {"file_path": "/home/user/project/src/auth.py"}),
    ], usage(10, 50, 3000), t)
    lines.append(line)
    t += 3

    # Assistant reads another file
    aid2, line = assistant_msg(aid, [
        tool_use("Read", {"file_path": "/home/user/project/src/models.py"}),
    ], usage(10, 30, 5000), t)
    lines.append(line)
    t += 3

    # Assistant does a grep
    aid3, line = assistant_msg(aid2, [
        tool_use("Grep", {"pattern": "session", "path": "/home/user/project/src"}),
    ], usage(10, 40, 7000), t)
    lines.append(line)
    t += 3

    # *** WASTE: Re-reads auth.py ***
    aid4, line = assistant_msg(aid3, [
        text_block("세션 관련 코드를 다시 확인합니다."),
        tool_use("Read", {"file_path": "/home/user/project/src/auth.py"}),
    ], usage(10, 50, 9000), t)
    lines.append(line)
    t += 3

    # Assistant searches but doesn't use the result
    aid5, line = assistant_msg(aid4, [
        tool_use("Glob", {"pattern": "**/*.test.py", "path": "/home/user/project"}),
    ], usage(10, 20, 11000), t)
    lines.append(line)
    t += 3

    # *** WASTE: unused glob — goes straight to editing ***
    aid6, line = assistant_msg(aid5, [
        text_block("리팩토링을 시작합니다."),
        tool_use("Edit", {"file_path": "/home/user/project/src/auth.py", "old_string": "class Auth:", "new_string": "class AuthManager:"}),
    ], usage(10, 200, 13000), t)
    lines.append(line)
    t += 5

    # Creates new session module
    aid7, line = assistant_msg(aid6, [
        tool_use("Write", {"file_path": "/home/user/project/src/session.py", "content": "class SessionManager:\n    pass"}),
    ], usage(10, 300, 15000), t)
    lines.append(line)
    t += 5

    # *** WASTE: Re-reads auth.py AGAIN ***
    aid8, line = assistant_msg(aid7, [
        tool_use("Read", {"file_path": "/home/user/project/src/auth.py"}),
    ], usage(10, 40, 17000), t)
    lines.append(line)
    t += 3

    # More edits
    aid9, line = assistant_msg(aid8, [
        tool_use("Edit", {"file_path": "/home/user/project/src/auth.py", "old_string": "def login(", "new_string": "def authenticate("}),
    ], usage(10, 150, 19000), t)
    lines.append(line)
    t += 5

    # *** WASTE: Re-reads models.py ***
    aid10, line = assistant_msg(aid9, [
        tool_use("Read", {"file_path": "/home/user/project/src/models.py"}),
    ], usage(10, 30, 21000), t)
    lines.append(line)
    t += 3

    # Unused search
    aid11, line = assistant_msg(aid10, [
        tool_use("Grep", {"pattern": "import auth", "path": "/home/user/project"}),
    ], usage(10, 25, 23000), t)
    lines.append(line)
    t += 3

    # Another edit (not related to search results)
    aid12, line = assistant_msg(aid11, [
        tool_use("Write", {"file_path": "/home/user/project/src/session.py", "content": "class SessionManager:\n    def create(self): pass\n    def destroy(self): pass"}),
    ], usage(10, 250, 25000), t)
    lines.append(line)
    t += 5

    # Test run
    aid13, line = assistant_msg(aid12, [
        tool_use("Bash", {"command": "cd /home/user/project && python -m pytest tests/"}),
    ], usage(10, 100, 27000), t)
    lines.append(line)
    t += 10

    # *** WASTE: Re-reads auth.py a 4th time ***
    aid14, line = assistant_msg(aid13, [
        text_block("테스트 실패를 확인합니다."),
        tool_use("Read", {"file_path": "/home/user/project/src/auth.py"}),
    ], usage(10, 45, 29000), t)
    lines.append(line)
    t += 3

    # Fix and final edit
    aid15, line = assistant_msg(aid14, [
        tool_use("Edit", {"file_path": "/home/user/project/src/auth.py", "old_string": "from session", "new_string": "from .session"}),
    ], usage(10, 120, 31000), t)
    lines.append(line)
    t += 5

    # Many turns with high cache read and tiny output (duplicate context pattern)
    prev = aid15
    for i in range(8):
        prev, line = assistant_msg(prev, [
            text_block("확인 중..." if i % 2 == 0 else "계속 진행합니다."),
        ], usage(5, 3, 33000 + i * 2000), t)
        lines.append(line)
        t += 2

    # Final summary
    final, line = assistant_msg(prev, [
        text_block("리팩토링이 완료되었습니다. auth.py에서 세션 관리 로직을 session.py로 분리했습니다."),
    ], usage(10, 200, 50000), t)
    lines.append(line)

    return "\n".join(lines)


if __name__ == "__main__":
    import pathlib
    out = pathlib.Path(__file__).parent / "sample_session.jsonl"
    out.write_text(generate())
    print(f"Generated: {out}")
