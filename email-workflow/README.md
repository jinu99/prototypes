# 읽기전용 이메일 AI 분류기

> IMAP EXAMINE 모드로 이메일을 읽고, 로컬 LLM(Ollama) 또는 키워드 규칙으로 분류하는 CLI 도구

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  IMAP Server │────▶│  ImapReader  │────▶│    Parser    │
│  (EXAMINE)   │     │  (read-only) │     │  (MIME→text) │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
       ┌──────────────┐     ┌──────────────┐     │
       │   Terminal    │◀────│   Digest /   │◀────┤
       │   (rich)      │     │   Thread     │     │
       └──────────────┘     └──────────────┘     │
                                                 ▼
                            ┌──────────────┐  ┌──────────────┐
                            │   Ollama     │  │   SQLite     │
                            │  (or rules)  │  │   Cache      │
                            └──────────────┘  └──────────────┘
```

## Demo

### connect — 이메일 fetch
```
$ email-classify --demo connect
⚡ Demo mode — using sample emails

✓ 20 emails fetched and cached to SQLite

╭── IMAP Log (read-only verification) ──╮
│ [IMAP] DEMO_MODE: Using generated...  │
╰───────────────────────────────────────╯
No SELECT, STORE, DELETE, or COPY commands used — server unchanged
```

### digest — 분류 + 다이제스트
```
$ email-classify digest
Classifying 20 emails...
✓ Classification complete

╭──── 📬 Daily Digest ─────╮
│ 오늘 중요한 이메일 13개  │
╰──────────────────────────╯
 ★  카테고리   발신자          제목
★★★ security  Google          Security alert: New sign-in from Windows
 ★★ work      진우            Re: 위클리 미팅 안건 공유
 ★★ work      GitHub          Re: PR #432: Fix authentication redirect loop
 ★★ finance   AWS             AWS Billing Alert: Estimated charges exceed $100
  · marketing Netflix         New on Netflix: Shows you might like
  · newsletter Substack       The Pragmatic Engineer: How Big Tech Does Code Review

분류 분포: work: 10 │ finance: 2 │ shopping: 2 │ marketing: 2 │ ...
```

### thread — 스레드 요약
```
$ email-classify thread demo-001@email-classify.local
╭──── 🧵 Thread Summary ────╮
│ Thread: PR #432: Fix ...   │
│ Messages: 3                │
╰───────────────────────────╯
  ├─ 2026-03-17 07:00  GitHub  PR #432: Fix authentication redirect loop
  ├─ 2026-03-17 13:49  김민재  Re: LGTM! Just one minor comment...
  └─ 2026-03-18 02:38  GitHub  Re: minjae approved. Merging now.
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 데모 모드 (IMAP 서버 불필요)
uv run email-classify --demo connect
uv run email-classify digest
uv run email-classify thread demo-001@email-classify.local

# 실제 IMAP 서버 연결
export IMAP_HOST=imap.gmail.com
export IMAP_USER=your@gmail.com
export IMAP_PASS=your-app-password
uv run email-classify connect
uv run email-classify digest
```

## 구조

```
email-workflow/
├── email_classify/
│   ├── __init__.py          # 패키지
│   ├── cli.py               # CLI 엔트리포인트 (click)
│   ├── imap_client.py       # IMAP EXAMINE 모드 클라이언트
│   ├── parser.py            # MIME 파싱 + 텍스트 추출
│   ├── classifier.py        # Ollama LLM + 키워드 규칙 fallback
│   ├── db.py                # SQLite 캐시
│   └── demo_data.py         # 20개 샘플 이메일 생성
├── pyproject.toml
├── BUILD_LOG.md
├── STATUS.md
└── README.md
```

## 원본
prototype-pipeline spec: email-workflow
