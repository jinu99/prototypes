---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Runtime Debug Bridge

**AI 코딩 에이전트가 실행 중인 앱의 런타임 컨텍스트를 직접 조회할 수 있는 MCP 디버깅 브릿지**

- 카테고리: Developer Tools / AI Agent Infra
- 스택: Python, asyncio, SQLite, MCP SDK, uv
- 날짜: 2026-03-02

<!--
AI 코딩 도구를 쓰다 보면, 코드를 고쳐달라고 할 때는 꽤 잘 하는데, 디버깅을 시키면 갑자기 무력해지는 순간이 있다. 코드는 읽을 수 있는데 실행 시점에 뭐가 일어나는지는 모르기 때문이다. 결국 try-catch를 덕지덕지 붙이거나 "이거 아닐까?" 하고 추측만 하게 된다. 오늘 보여줄 건 그 문제를 정면으로 다뤄본 프로토타입이다.
-->

---

## Background

### AI 코딩 에이전트의 사각지대

- AI 코딩 에이전트(Claude Code, Codex 등)는 **소스 코드는 읽을 수 있지만**, 실행 시점의 정보는 볼 수 없다
- 네트워크 요청, 상태 변경, stderr 로그, 타이밍 정보 — 전부 블랙박스
- 결과: 근본 원인을 **추측**하거나, 무의미한 try/catch를 추가하는 수준에 그침

### 왜 지금 이슈인가

- MCP(Model Context Protocol)가 등장하면서, AI 에이전트에 **외부 도구를 연결하는 표준**이 생김
- 코드를 읽는 것 이상으로, **런타임을 관찰하는 것**이 가능해진 시점
- 그런데 아직 이걸 제대로 연결한 도구가 없다

<!--
AI 코딩 에이전트가 코드를 잘 읽는다는 건 이제 다들 아는 사실이다. 문제는 디버깅이다. 버그를 고치려면 코드만 봐서는 안 되고, 실행 시점에 뭐가 일어나고 있는지를 알아야 한다. 네트워크 요청이 실패했는지, stderr에 뭐가 찍혔는지, 프로세스가 어떤 상태인지. 사람으로 치면, 의사가 환자의 MRI 사진만 보고 수술하는 것과 마찬가지다. 생체 신호를 실시간으로 봐야 한다. MCP라는 프로토콜이 나오면서 이걸 연결할 수 있는 길이 열렸는데, 아직 범용적으로 이걸 해주는 도구가 없다.
-->

---

## Pain Point

### 커뮤니티에서 반복적으로 나오는 고통

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/SideProject | ⬤⬤⬤ | AI 코딩 어시스턴트가 런타임 정보(네트워크, 상태, 로그)를 볼 수 없어 **디버깅 시 원인을 추측**한다 |
| 2 | r/LocalLLaMA | ⬤⬤⬤ | 타이밍에 민감한 간헐적 버그는 **재시작 자체가 재현 조건을 변경**시킨다 |
| 3 | Hacker News | ⬤⬤⬤ | 프로덕션 DB에서 버그 재현에 필요한 **데이터 슬라이스 추출이 어렵다** |

### 공통 패턴

> 버그 발견 → 컨텍스트 수집 → 재현 환경 구축
> 이 워크플로의 **매 단계마다 병목**이 있다

<!--
Reddit이나 Hacker News에서 이런 얘기가 계속 나온다. AI 코딩 도구가 좋은데, 런타임 정보를 못 보니까 결국 사람이 직접 로그를 복사해서 붙여넣기 해야 한다는 거다. 그리고 간헐적 버그 같은 경우는 더 심각하다. 재시작하면 조건이 바뀌어서 재현이 안 된다. 결국 이건 디버깅 워크플로 전체의 문제다. 버그를 발견하고, 컨텍스트를 모으고, 재현 환경을 만드는 매 단계에서 병목이 생긴다. 세 곳 모두 signal strength가 3으로, 꽤 강한 신호다.
-->

---

## Solution

### 접근법

**앱을 subprocess로 감싸서 런타임 데이터를 자동 캡처하고, MCP로 AI 에이전트에 노출한다**

### 기존 솔루션과 다른 점

| 기존 | Runtime Debug Bridge |
|------|---------------------|
| DB 서브셋 추출만 (dbslice, Jailer) | 런타임 캡처 + MCP 연동 통합 |
| 특정 프레임워크 종속 MCP 서버들 | **범용** — 어떤 프로세스든 래핑 가능 |
| 로그를 사람이 복사-붙여넣기 | AI 에이전트가 **직접 조회** |

### 검증 목표

> AI 코딩 에이전트에 런타임 컨텍스트를 구조화하여 제공하면,
> 추측 기반 디버깅에서 벗어나 **근본 원인 도달 시간을 단축**할 수 있는가?

<!--
접근법은 단순하다. 대상 앱을 subprocess로 감싸서 stdout, stderr를 실시간으로 캡처하고, HTTP 프록시를 주입해서 아웃바운드 트래픽도 잡는다. 이걸 SQLite에 저장해두고, MCP 서버로 AI 에이전트가 직접 조회할 수 있게 한다. 기존에도 비슷한 시도가 있었는데, 대부분 특정 프레임워크에 종속되어 있거나 DB 추출만 하는 도구들이다. 이 도구는 범용적이다. Python 앱이든 Node 앱이든, 프로세스로 실행할 수 있으면 래핑할 수 있다.
-->

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│  AI 에이전트 (Claude Code)                        │
│  "최근 에러 로그 보여줘"                           │
└──────────────┬───────────────────────────────────┘
               │ JSON-RPC (stdio)
               ▼
┌──────────────────────────────────────────────────┐
│  MCP Server (mcp_server.py)                       │
│  ┌─────────────────┬──────────────┬────────────┐ │
│  │ get_recent_logs │ get_http     │ get_process │ │
│  │     _tool       │ _traffic_tool│ _state_tool │ │
│  └────────┬────────┴──────┬───────┴──────┬─────┘ │
└───────────┼───────────────┼──────────────┼───────┘
            ▼               ▼              ▼
     ┌────────────┐  ┌───────────┐  ┌───────────┐
     │  SQLite    │  │  SQLite   │  │  /proc    │
     │  logs      │  │  http     │  │  filesystem│
     └─────┬──────┘  └─────┬─────┘  └───────────┘
           └────────┬──────┘
                    ▼
┌──────────────────────────────────────────────────┐
│  Capture Engine (capture.py)                      │
│  ┌───────────────────┐  ┌──────────────────────┐ │
│  │ subprocess 래핑    │  │ HTTP Forward Proxy   │ │
│  │ asyncio PIPE      │  │ HTTP_PROXY 자동 주입  │ │
│  └───────────────────┘  └──────────────────────┘ │
│               └──────┬───────┘                    │
│                      ▼                            │
│             ┌──────────────┐                      │
│             │  대상 앱     │                      │
│             └──────────────┘                      │
└──────────────────────────────────────────────────┘
```

<!--
아키텍처는 세 층으로 나뉜다. 맨 아래 Capture Engine이 대상 앱을 subprocess로 감싸서 stdout, stderr를 asyncio PIPE로 실시간 캡처한다. 동시에 HTTP 포워드 프록시를 띄워서 아웃바운드 요청도 잡는다. 이 데이터가 SQLite에 쌓이고, 맨 위의 MCP 서버가 세 개의 도구로 이걸 노출한다. AI 에이전트는 JSON-RPC를 통해 자연어로 질의하면 된다. 프로세스 상태는 별도로 /proc 파일시스템에서 직접 읽는다.
-->

---

## Demo

### 앱 래핑 → 캡처 → MCP 조회 E2E

```
$ uv run rdb wrap -- python3 examples/buggy_app.py

[rdb] Session: a1b2c3d4e5f6
[rdb] HTTP proxy: http://127.0.0.1:54321
[rdb] Running: python3 examples/buggy_app.py
[rdb] ---
Starting buggy app...
Making HTTP request to httpbin.org...
ERROR: Something went wrong!
ZeroDivisionError: division by zero
[rdb] ---
[rdb] Process exited with code 1
```

### MCP 도구 호출 결과

```
[MCP] get_recent_logs_tool → Error logs (3 lines):
  [stderr] ERROR: Something went wrong!
  [stderr] ZeroDivisionError: division by zero

[MCP] get_http_traffic_tool → HTTP requests (2 captured):
  GET http://httpbin.org/get → 200
  POST http://httpbin.org/post → 200

[MCP] get_process_state_tool → PID: 54321
  Memory: RSS=28416 KB | Open FDs: 8
```

<!--
실제로 돌려보면 이런 흐름이다. buggy_app이라는 의도적으로 버그를 넣은 앱을 rdb wrap으로 감싸서 실행한다. 앱이 죽으면, AI 에이전트가 MCP 도구로 바로 조회할 수 있다. 에러 로그만 필터링해서 볼 수도 있고, HTTP 트래픽을 확인해서 외부 API 호출이 문제였는지도 바로 알 수 있다. 사람이 로그를 복사해서 붙여넣을 필요가 없다. 에이전트가 직접 가져간다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 판단 | 선택 | 이유 |
|------|------|------|
| HTTP 캡처 방식 | stdlib `http.server` 포워드 프록시 | 외부 의존성 없이 아웃바운드 캡처. eBPF/ptrace는 범위 초과 |
| 스트림 캡처 | asyncio subprocess PIPE | 실시간 line-by-line 캡처. 순서는 삽입 순 보장 (ORDER BY id) |
| 저장소 | SQLite (stdlib) | 세션 단위 관리, 별도 서버 불필요. cross_thread 이슈 해결 필요 |

### 시행착오

- **SQLite thread safety**: 프록시가 별도 스레드에서 돌아 `check_same_thread=False` 필요 → `get_db(cross_thread=True)` 옵션 추가
- **procinfo bytes 처리**: `/proc/cmdline`은 null-byte로 구분된 bytes → decode 후 join으로 수정
- **로그 순서 문제**: timestamp 기반 정렬 시 삽입 순서와 불일치 → `ORDER BY id`로 변경

### 심의 점수

문제 진정성 **4.0** · 학습 가치 **4.3** · 프로토타입 적합성 3.0 · 신선도 3.0

<!--
스택 선택에서 의도적으로 외부 의존성을 최소화했다. MCP SDK만 외부에서 가져오고, 나머지는 전부 stdlib으로 해결했다. HTTP 캡처 같은 경우 eBPF를 쓰면 더 강력하겠지만, 프로토타입 범위에서는 HTTP_PROXY 환경변수를 주입하는 포워드 프록시가 적절하다. 시행착오도 꽤 있었는데, SQLite가 멀티스레드에서 기본적으로 안 되는 부분이라든가, /proc에서 바이트를 읽을 때 인코딩 문제라든가. 솔직히 이런 건 직접 부딪혀봐야 아는 것들이다. 심의에서 학습 가치를 4.3으로 꽤 높게 받았는데, MCP 서버 구현이나 subprocess 래핑 같은 부분에서 배울 게 많은 프로토타입이었다.
-->

---

## Results & Future

### 성과 — 5/5 완료 기준 통과

- ✅ `rdb wrap` stdout/stderr 실시간 캡처 → SQLite 저장
- ✅ 내장 HTTP 프록시 아웃바운드 요청/응답 캡처
- ✅ `/proc` 기반 프로세스 상태 구조화된 JSON 반환
- ✅ MCP 서버 3개 도구 노출 및 정상 응답
- ✅ Claude Code 연동 E2E 데모 성공

### 한계점

- HTTPS 트래픽은 캡처 불가 (프록시 모드 한계)
- stderr/stdout 순서가 버퍼링 특성상 약간 뒤섞일 수 있음
- Linux 전용 (/proc 파일시스템 의존)

### 프로덕트가 되려면

- **HTTPS 지원**: mitmproxy 연동 또는 CA 인증서 주입
- **상태 스냅샷 트리거**: 간헐적 버그 발생 시점의 상태를 자동 덤프
- **DB 데이터 슬라이스**: 에러 로그에서 레코드 ID 추출 → FK 관계 따라 최소 데이터셋 생성
- **크로스 플랫폼**: macOS/Windows 프로세스 상태 조회 지원

<!--
완료 기준 다섯 개를 전부 통과했다. 결과적으로 이 프로토타입이 검증한 건, AI 에이전트에 런타임 컨텍스트를 MCP로 연결하면 실제로 쓸 만하다는 거다. 솔직히 한계는 있다. HTTPS는 못 잡고, 리눅스에서만 돌아간다. 하지만 핵심 가설은 확인됐다. 에이전트가 로그를 직접 가져가서 분석하는 경험은, 사람이 복사-붙여넣기 하는 것과는 질적으로 다르다. 프로덕트가 되려면 HTTPS 지원이랑 크로스 플랫폼이 필수인데, 이건 결국 엔지니어링 노력의 문제이지 방향의 문제는 아니다.
-->
