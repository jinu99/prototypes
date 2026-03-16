# Local Email Inbox Cleaner

> IMAP 헤더 메타데이터만으로 뉴스레터·마케팅·알림 이메일을 자동 분류하고 정리 제안을 생성하는 CLI 도구

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│   IMAP Server       │     │   Mock Generator     │
│  (Gmail, etc.)      │     │  (mock_data.py)      │
└────────┬────────────┘     └────────┬────────────┘
         │ IMAP FETCH HEADER                │ 12,000개 생성
         ▼                                  ▼
┌──────────────────────────────────────────────────┐
│              imap_client.py                      │
│  헤더 파싱: From, Subject, List-Unsubscribe,     │
│  X-Mailer, Precedence, Date, Size               │
└────────────────────┬─────────────────────────────┘
                     │ upsert
                     ▼
            ┌─────────────────┐
            │   SQLite (WAL)  │
            │   emails.db     │
            └───┬─────┬───┬───┘
                │     │   │
       ┌────────┘     │   └────────┐
       ▼              ▼            ▼
┌─────────────┐ ┌──────────┐ ┌──────────────┐
│ classifier  │ │ analyzer │ │   cleanup    │
│  .py        │ │  .py     │ │    .py       │
│             │ │          │ │              │
│ 6개 시그널: │ │ 발신자별 │ │ dry run      │
│ ·Unsubscribe│ │  통계    │ │  → 영향 미리 │
│ ·Precedence │ │ 카테고리 │ │    보기      │
│ ·X-Mailer   │ │  요약    │ │ execute      │
│ ·Domain     │ │ 구독해지 │ │  → 로컬 삭제 │
│ ·Subject    │ │  후보    │ │  → IMAP 삭제 │
│ ·Age        │ │          │ │    /아카이브  │
└──────┬──────┘ └────┬─────┘ └──────┬───────┘
       │             │              │
       └──────┬──────┘──────────────┘
              ▼
     ┌──────────────────┐
     │     tui.py       │
     │  Rich TUI 출력   │
     │                  │
     │ · Category 요약  │
     │ · Top 발신자     │
     │ · Unsub 후보     │
     │ · Cleanup 미리보기│
     └──────────────────┘
```

## Demo

```bash
# 전체 파이프라인 데모 실행 (mock 데이터 12,000개)
$ uv run python main.py all
```

```
Loading mock data...
Loaded 12,000 mock emails in 0.8s

Classifying emails...
Classification complete in 1.2s:
  newsletter: 3,240
  marketing: 2,880
  notification: 2,160
  old: 1,920
  personal: 1,800

╔══════════════════════════════════╗
║         Inbox Cleaner           ║
║      12,000 emails analyzed     ║
╚══════════════════════════════════╝

╭──────────────────────────────────────────────────╮
│            Category Summary                       │
├────────────────┬───────┬────────┬────────────────┤
│ Category       │ Count │ Unread │ Total Size     │
├────────────────┼───────┼────────┼────────────────┤
│ newsletter     │ 3,240 │ 2,430  │ 48.6 MB        │
│ marketing      │ 2,880 │ 2,304  │ 57.6 MB        │
│ notification   │ 2,160 │ 1,080  │ 21.6 MB        │
│ old            │ 1,920 │   960  │ 28.8 MB        │
│ personal       │ 1,800 │   540  │ 18.0 MB        │
╰────────────────┴───────┴────────┴────────────────╯

┌─────────────────────────────────────────────────────────────┐
│ DRY RUN — Preview of cleanup impact                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  NEWSLETTER (3,240 emails, 48.6 MB)                         │
│    weekly@techdigest.com          420                        │
│    newsletter@producthunt.com     380                        │
│                                                             │
│  MARKETING (2,880 emails, 57.6 MB)                          │
│    promo@shopping.com             350                        │
│    deals@travel.com               290                        │
│                                                             │
│  Total cleanup: 10,200 emails | 156.6 MB recoverable       │
└─────────────────────────────────────────────────────────────┘
```

```bash
# 개별 단계 실행
$ uv run python main.py fetch --mock           # mock 데이터 로드
$ uv run python main.py classify               # 휴리스틱 분류
$ uv run python main.py analyze --top 10       # 상위 10 발신자 분석
$ uv run python main.py dryrun                 # 정리 영향 미리보기
$ uv run python main.py clean --force          # 로컬 캐시에서 정리 실행
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 전체 데모 (mock 데이터로 fetch → classify → analyze → dryrun)
uv run python main.py all

# 개별 명령어
uv run python main.py fetch --mock          # mock 데이터 12,000개 로드
uv run python main.py classify              # 휴리스틱 분류 실행
uv run python main.py analyze               # 분석 대시보드 표시
uv run python main.py analyze --top 10      # 상위 10 발신자만
uv run python main.py dryrun                # 정리 영향 미리보기
uv run python main.py clean --force         # 로컬 캐시에서 정리 실행

# 실제 IMAP 서버 사용
uv run python main.py fetch --host imap.gmail.com --user you@gmail.com --password APP_PASSWORD
uv run python main.py clean --imap --host imap.gmail.com --user you@gmail.com --password APP_PASSWORD
```

## 구조

```
local-email-cleanup/
├── main.py              # CLI 진입점 (fetch/classify/analyze/dryrun/clean/all)
├── mock_data.py         # 테스트용 mock 이메일 생성기 (12,000개)
├── src/
│   ├── db.py            # SQLite 스키마 & 쿼리 (WAL 모드)
│   ├── imap_client.py   # IMAP 연결/fetch + mock 로더
│   ├── classifier.py    # 휴리스틱 분류기 (6개 시그널, 88% 정확도)
│   ├── analyzer.py      # 발신자 통계 & 구독 해지 후보 분석
│   ├── cleanup.py       # 드라이런 + 실제 삭제/아카이브 실행
│   └── tui.py           # Rich TUI (테이블, 패널, 색상)
├── BUILD_LOG.md         # 빌드 일지
├── STATUS.md            # 완료 상태
└── pyproject.toml       # uv 프로젝트 설정
```

## 분류 시그널

1. `List-Unsubscribe` 헤더 존재 → 뉴스레터/마케팅
2. `Precedence: bulk/list` → 대량 발송/메일링 리스트
3. `X-Mailer` (Mailchimp, SendGrid 등) → 마케팅
4. 발신자 도메인 패턴 (github.com, slack.com 등) → 알림
5. Subject 키워드 (sale, discount, digest, weekly 등)
6. 이메일 나이 (6개월+) → 오래된 메일

## 원본
prototype-pipeline spec: local-email-cleanup
