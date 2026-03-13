# Agentic Coding Workspace

> 셀 기반 인터페이스에서 AI 에이전트 플랜을 사전 검토·수정하고 셀 단위로 재실행하는 코딩 워크스페이스 프로토타입

## 실행 방법

```bash
# 브라우저에서 직접 열기 (의존성 없음)
open index.html        # macOS
xdg-open index.html    # Linux

# 또는 간단한 HTTP 서버 사용
npx serve .
```

## 사용법

1. **Demo** 버튼을 클릭하면 사전 준비된 코딩 시나리오가 로드됩니다
2. 프롬프트 셀에 코딩 작업을 입력하고 **Run** (또는 `Ctrl+Enter`) 클릭
3. **Plan Preview**가 표시되면 항목을 수정/삭제/체크 해제 후 **Approve & Execute** 클릭
4. 결과가 스트리밍으로 표시됩니다
5. 완료 후 **Re-run** 버튼으로 같은 셀을 다시 실행할 수 있습니다
6. 셀 상태는 LocalStorage에 자동 저장되어 새로고침 후에도 유지됩니다

## 테스트

```bash
npm install
node test.js
```

## 구조

```
agentic-coding-workspace/
├── index.html      # 진입점 (HTML 구조)
├── style.css       # 다크 테마 스타일
├── mock-data.js    # Mock AI 응답 시나리오
├── render.js       # 셀 DOM 렌더링 함수
├── app.js          # 핵심 로직 (셀 관리, 실행, 저장)
├── test.js         # jsdom 기반 기능 테스트 (30개)
├── BUILD_LOG.md    # 빌드 일지
├── STATUS.md       # 프로토타입 상태
└── README.md       # 이 파일
```

## 원본
prototype-pipeline spec: agentic-coding-workspace
