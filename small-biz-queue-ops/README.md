# Small Biz Queue Ops

> QR 코드 기반 매장 대기열 관리 시스템 — 실시간 대기 순서 표시, 매장 관리, KDS 뷰

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        클라이언트 (Browser)                       │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ │
│  │ index.html │  │ join.html  │  │ admin.html │  │  kds.html  │ │
│  │  홈 / QR   │  │ 대기 등록  │  │ 매장 관리  │  │  KDS 뷰   │ │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘ │
│        │               │               │               │        │
│        └───────────┬────┴───────────────┴───────┬───────┘        │
│              REST API (fetch)            SSE (EventSource)       │
└──────────────────┬───────────────────────────┬───────────────────┘
                   │                           │
                   ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      server.js (HTTP 서버)                       │
│                                                                  │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │   정적 파일 서빙     │    │         API 라우팅               │ │
│  │   public/ ─▶ 응답    │    │  POST /api/queue     대기 등록   │ │
│  └─────────────────────┘    │  GET  /api/queue     목록 조회   │ │
│                              │  GET  /api/queue/all 전체 조회   │ │
│                              │  PATCH /api/queue/:id/status     │ │
│                              │  GET  /api/queue/:id 개별 조회   │ │
│                              │  GET  /api/qrcode   QR 생성     │ │
│                              │  GET  /api/events   SSE 연결    │ │
│                              └──────────┬───────────────────────┘ │
│                                         │                        │
│          ┌──────────────────────────────┼────────────────┐       │
│          ▼                              ▼                │       │
│  ┌──────────────┐              ┌──────────────┐          │       │
│  │   routes.js  │──── 변경 ──▶│   sse.js     │          │       │
│  │  대기열 CRUD │   broadcast  │  SSE 관리    │          │       │
│  │  QR 코드 생성│              │  실시간 푸시  │          │       │
│  └──────┬───────┘              └──────┬───────┘          │       │
│         │                             │                  │       │
│         ▼                             ▼                  │       │
│  ┌──────────────┐          클라이언트에 queue-update      │       │
│  │    db.js     │          이벤트 broadcast               │       │
│  │   SQLite     │                                        │       │
│  │  (queue.db)  │                                        │       │
│  └──────────────┘                                        │       │
└──────────────────────────────────────────────────────────────────┘
```

**핵심 데이터 흐름:**
1. 고객이 QR 코드를 스캔하여 `/join` 페이지에서 대기 등록 (`POST /api/queue`)
2. `routes.js`가 SQLite에 저장 후 `sse.js`를 통해 전체 클라이언트에 실시간 broadcast
3. 관리자(`/admin`)가 상태 변경 시 (`PATCH /api/queue/:id/status`) 동일하게 broadcast
4. KDS(`/kds`)와 홈(`/`) 페이지가 SSE로 실시간 업데이트 수신

## Demo

### 서버 실행

```bash
npm install
npm start
# 🏪 Small Biz Queue Ops running at http://localhost:3000
#    고객 등록: http://localhost:3000/join
#    매장 관리: http://localhost:3000/admin
#    KDS 뷰:   http://localhost:3000/kds
```

### API 사용 예시

**대기 등록:**
```bash
curl -X POST http://localhost:3000/api/queue \
  -H "Content-Type: application/json" \
  -d '{"name": "홍길동", "party_size": 4}'

# {"id":1,"name":"홍길동","party_size":4,"status":"waiting",
#  "position":1,"estimated_wait":0, ...}
```

**대기열 조회:**
```bash
curl http://localhost:3000/api/queue

# [{"id":1,"name":"홍길동","party_size":4,"status":"waiting",
#   "position":1,"estimated_wait":0, ...}]
```

**상태 변경 (호출):**
```bash
curl -X PATCH http://localhost:3000/api/queue/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "called"}'

# {"id":1,"name":"홍길동","status":"called","called_at":"2026-03-16 14:30:00", ...}
```

**QR 코드 생성:**
```bash
curl http://localhost:3000/api/qrcode?url=http://localhost:3000/join

# {"qr":"data:image/png;base64,...","url":"http://localhost:3000/join"}
```

### 주요 화면

| 경로 | 설명 |
|------|------|
| `http://localhost:3000/` | QR 코드와 현재 대기 현황을 실시간으로 표시하는 홈 화면 |
| `http://localhost:3000/join` | 고객이 QR 스캔 후 이름과 인원수를 입력하여 대기 등록 |
| `http://localhost:3000/admin` | 매장 관리자가 대기자 목록을 확인하고 상태(호출/착석/완료)를 변경 |
| `http://localhost:3000/kds` | 주방/카운터 디스플레이용 카드 형태의 대기 상태 모니터 |

## 실행 방법

```bash
# 의존성 설치
npm install

# 실행
npm start
```

서버가 `http://localhost:3000`에서 시작됩니다.

## 페이지

| 경로 | 용도 |
|------|------|
| `/` | 홈 — QR 코드 표시 + 대기 현황 |
| `/join` | 고객 대기 등록 (QR 스캔 시 이동) |
| `/admin` | 매장 관리 — 대기자 목록 + 상태 변경 |
| `/kds` | KDS — 카드 형태 대기 상태 디스플레이 |

## 구조

```
small-biz-queue-ops/
├── server.js          # HTTP 서버 (정적 파일 + API + SSE)
├── db.js              # SQLite 초기화
├── routes.js          # API 핸들러 (대기열 CRUD)
├── sse.js             # SSE 클라이언트 관리
├── public/
│   ├── index.html     # 홈 (QR + 현황)
│   ├── join.html      # 고객 등록
│   ├── admin.html     # 매장 관리
│   ├── kds.html       # KDS 뷰
│   ├── style.css      # 공통 스타일
│   └── manifest.webmanifest  # PWA manifest
├── BUILD_LOG.md       # 빌드 일지
├── STATUS.md          # 검증 결과
└── README.md
```

## 원본
prototype-pipeline spec: small-biz-queue-ops
