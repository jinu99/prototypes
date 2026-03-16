# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-14 — Spec 파일 읽기 완료
- [판단] 스택 선택: Python + uv (이유: Go/kubectl/kind/minikube 모두 미설치. Python 3.12 + uv 사용 가능. K8s API를 시뮬레이션하여 핵심 컨셉 검증)
- [판단] K8s 시뮬레이터 방식 채택 (이유: 실제 클러스터 없이도 배포 감지 → 로그 스트리밍 → 이상 감지 → 알림 흐름 전체를 검증 가능. 시뮬레이터를 분리하면 나중에 실제 kubernetes client로 교체 용이)
- [판단] 외부 의존성 0개 (이유: 표준 라이브러리만으로 CLI + 이벤트 시스템 + 비동기 처리 가능. asyncio 활용)

## Phase 2 — 구현
- [시도] 프로젝트 구조 생성 (uv init, soak/ 패키지) → [결과] 성공
- [시도] models.py — Pod, Deployment, Event 데이터 모델 → [결과] 성공
- [시도] cluster.py — SimulatedCluster (이벤트 시스템, 4개 시나리오 주입) → [결과] 성공
- [시도] patterns.py — 정규식 기반 에러 패턴 매칭 (9개 패턴) → [결과] 성공
- [시도] reporter.py — ANSI 컬러 터미널 출력 (배너, 이벤트, 경고, 프로그레스 바, 리포트) → [결과] 성공
- [시도] monitor.py — SoakMonitor 코어 (이벤트 워칭, 이상 감지, soak 윈도우) → [결과] 성공
- [시도] demo.py — 4개 시나리오 정의 (healthy, oom, crashloop, error_logs) → [결과] 성공
- [시도] cli.py — argparse CLI (`soak watch`, `soak scenarios`) → [결과] 성공
- [시도] healthy 시나리오 실행 → [결과] 성공, ALL CLEAR 리포트 출력
- [시도] oom 시나리오 실행 → [결과] 성공, OOMKilled 감지 + 롤백 제안
- [시도] crashloop 시나리오 실행 → [결과] 성공, 3회 재시작 감지
- [시도] error_logs 시나리오 실행 → [결과] 성공, panic/fatal/connection_refused 감지

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → 솔직히 "오 되네" 쪽. 터미널 출력이 색상+아이콘으로 직관적이고, 시나리오별 데모가 깔끔함
- [평가] Spec 검증 목표 → 배포 감지 → 로그 모니터링 → 이상 감지 → 알림 흐름 전체 검증됨
- [불만] error_logs 시나리오에서 동일 로그에 connection_refused + error_generic 중복 매칭 → [개선] 가장 높은 severity 패턴만 보고하도록 수정
- [평가] 수정 후 재확인 → 깔끔해짐, 만족

## Phase 4 — 검증
- [체크] `soak watch <namespace>` → Deployment 변경 자동 감지 → 통과
- [체크] 새 pod 로그 스트리밍 + 에러 패턴 매칭 → 통과
- [체크] soak 윈도우 기본값 + `--duration` 플래그 → 통과 (10s, 15s, 20s 모두 확인)
- [체크] 이상 감지 시 경고 + `kubectl rollout undo` 명령 제안 → 통과
- [체크] 의도적 장애 배포 → 감지 데모 시나리오 → 통과 (4개 시나리오 모두)
