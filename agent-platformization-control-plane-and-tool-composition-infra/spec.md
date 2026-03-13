# Agent Control Plane — Tool 조합 기반 에이전트 관리 플랫폼

> 원본 아이디어: 에이전트 플랫폼화 - Control Plane과 Tool 조합 기반 운영 인프라

## 검증 목표
`Agent = LLM + Tool Set + Permission` 조합 모델로 코드 변경 없이 에이전트를 동적 생성/관리/실행할 수 있는지 검증한다.

## 범위
- 포함:
  - Tool 레지스트리: 사용 가능한 Tool 목록 관리
  - Agent 정의: Tool Set + Permission + LLM 설정을 조합하여 Agent 역할 선언
  - Agent 인스턴스 CRUD: 생성, 조회, 수정, 삭제, 일시정지/재개
  - Agent 실행: 인스턴스에 메시지를 보내면 설정된 Tool Set 기반으로 응답 (Mock LLM)
  - 모니터링: 인스턴스별 상태, 실행 횟수, 에러 수 추적
  - 어드민 대시보드: 위 기능을 웹 UI로 조작

- 제외:
  - 실제 LLM 연동 (Mock으로 대체)
  - 멀티 노드 분산 실행
  - 인증/인가 시스템
  - 에이전트 간 통신 (오케스트레이션)
  - 메모리 시스템 (컨텍스트 유지)

## 기술 스택
- **Python + FastAPI**: 경량 REST API 서버 (비동기, 자동 OpenAPI 문서)
- **SQLite**: 에이전트/인스턴스/실행 로그 영속화
- **단일 HTML + vanilla JS**: 어드민 대시보드 (프레임워크 없음)
- **uv**: Python 의존성 관리

이유: 핵심은 "조합 모델"과 "CRUD 관리"의 검증이므로 가벼운 웹 서버 + DB면 충분. FastAPI는 자동 API 문서 제공으로 프로토타입 시연에 유리.

## 완료 기준
- [ ] Tool 레지스트리에 3종 이상의 Mock Tool 등록 및 조회 가능
- [ ] Tool Set + Permission 조합으로 Agent 정의를 생성하고, 같은 LLM 위에 다른 역할의 Agent를 만들 수 있음
- [ ] Agent 인스턴스 CRUD (생성/조회/수정/삭제/일시정지) API가 동작
- [ ] Agent 인스턴스에 메시지를 보내면 Tool Set에 맞는 응답이 돌아옴 (Mock LLM 기반)
- [ ] 어드민 대시보드에서 Agent 목록, 상태, 실행 이력을 확인하고 CRUD 조작 가능
