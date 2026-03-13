# Slide Last-Mile Editor

> Marp 마크다운 슬라이드를 브라우저에서 시각적으로 편집하고, 원본 .md 파일과 블록 레벨 양방향 동기화

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
