# Small Biz Queue Ops

> QR 코드 기반 매장 대기열 관리 시스템 — 실시간 대기 순서 표시, 매장 관리, KDS 뷰

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
