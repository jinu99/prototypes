# Slide Last-Mile Editor

> Marp 마크다운 슬라이드를 브라우저에서 시각적으로 편집하고, 원본 .md 파일과 블록 레벨 양방향 동기화

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (index.html)                     │
│                                                                 │
│  ┌──────────────┐   ┌───────────────────┐   ┌───────────────┐  │
│  │ Slide Preview │   │  Source Editor     │   │  Diff Viewer  │  │
│  │ (contentedi-  │   │  (textarea,       │   │  (변경사항     │  │
│  │  table 편집)  │   │   실시간 동기화)  │   │   시각화)     │  │
│  └──────┬───────┘   └────────┬──────────┘   └───────┬───────┘  │
│         │ blur/drag           │ input (800ms)        │ toggle   │
└─────────┼────────────────────┼──────────────────────┼──────────┘
          │                    │                      │
          ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Express Server (server.js)                    │
│                                                                 │
│  POST /api/edit ──┐                                             │
│  (블록 단위 편집)  │   ┌──────────────┐   ┌──────────────────┐  │
│                    ├──▶│  Marp Core   │──▶│  HTML + CSS 응답 │  │
│  POST /api/slide ──┤   │  (렌더링 +    │   └──────────────────┘  │
│  (전체 저장)       │   │  source-line  │                         │
│                    │   │   매핑 주입)  │   ┌──────────────────┐  │
│  POST /api/style ──┘   └──────────────┘   │  sample.md       │  │
│  (위치 조정)                              │  (원본 파일 R/W) │  │
│                                           └──────────────────┘  │
│  GET /api/diff ────────▶ diff 라이브러리 ──▶ 변경사항 JSON       │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 데이터 흐름:**
1. **시각적 편집 → 마크다운 동기화**: Preview에서 텍스트 클릭/편집 → `data-source-line` 속성으로 원본 줄 번호 추적 → `POST /api/edit`으로 해당 블록만 교체
2. **소스 편집 → 프리뷰 동기화**: textarea 입력 → 800ms debounce → `POST /api/slide` → Marp 재렌더링 → Preview 갱신
3. **드래그 위치 조정**: 드래그 핸들로 요소 이동 → `POST /api/style` → 마크다운에 `<!-- style: ... -->` HTML 주석 삽입

## Demo

### 서버 실행

```bash
$ node server.js
Slide Last-Mile Editor running at http://localhost:4567
```

### 주요 화면

브라우저에서 `http://localhost:4567` 접속 시 3패널 에디터가 표시됩니다:

- **Preview 패널** (좌측): Marp로 렌더링된 슬라이드 미리보기. 각 텍스트 블록을 클릭하면 `contenteditable`로 인라인 편집 가능. 좌측 드래그 핸들(⁞)로 요소 위치 조정.
- **Source 패널** (우측): 원본 마크다운을 직접 편집. 입력 시 800ms 후 자동 저장 및 프리뷰 동기화.
- **Diff 패널**: 상단 `Diff` 버튼으로 토글. 원본 대비 변경사항을 추가(초록)/삭제(빨강)로 표시.

### API 엔드포인트

```bash
# 슬라이드 로드
$ curl http://localhost:4567/api/slide
{"markdown":"---\nmarp: true\n...","html":"<section>...","css":"..."}

# 특정 블록 편집 (sourceLine으로 대상 지정)
$ curl -X POST http://localhost:4567/api/edit \
  -H 'Content-Type: application/json' \
  -d '{"sourceLine": 5, "sourceEnd": 6, "newText": "# 새 제목"}'

# 변경사항 diff 조회
$ curl http://localhost:4567/api/diff
{"original":"...","current":"...","changes":[{"added":true,"value":"..."}]}
```

## 실행 방법

```bash
# 의존성 설치
npm install

# 실행
node server.js

# 브라우저에서 열기
# http://localhost:4567
```

환경변수 `PORT`로 포트 변경 가능 (기본값: 4567)

## 기능

- Marp 마크다운 렌더링 및 슬라이드 미리보기
- 슬라이드 위 텍스트 클릭 → contenteditable 인라인 편집 → 원본 .md 자동 업데이트
- 드래그 핸들로 요소 위치 조정 → .md에 인라인 스타일(CSS 주석) 반영
- 편집 전후 마크다운 diff 시각적 표시
- 소스 에디터에서 직접 마크다운 편집 → 실시간 프리뷰 동기화

## 구조

```
slide-lastmile-editor/
├── server.js          # Express 서버 (Marp 렌더링 + 파일 I/O API)
├── index.html         # 단일 HTML 프론트엔드 (에디터 UI)
├── sample.md          # 3장 샘플 Marp 슬라이드
├── test-e2e.js        # API 기반 e2e 테스트
├── BUILD_LOG.md       # 빌드 일지
├── STATUS.md          # 프로토타입 상태
└── package.json       # npm 의존성
```

## 원본
prototype-pipeline spec: slide-lastmile-editor
