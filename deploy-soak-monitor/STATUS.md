# STATUS: SUCCESS

## 요약
K8s 배포 이벤트를 시뮬레이션하고, soak 윈도우 동안 pod 상태/로그를 실시간 감시하여 OOMKilled, CrashLoopBackOff, 에러 로그 패턴을 자동 감지하는 CLI 프로토타입.

## 완료 기준 결과
- [x] `soak watch <namespace>` 실행 시 해당 네임스페이스의 Deployment 변경을 자동 감지
- [x] 감지된 배포의 새 pod들에 대해 로그 스트리밍 + 에러 패턴 매칭이 동작
- [x] soak 윈도우(기본 15분, `--duration` 플래그로 변경 가능) 동안 pod 재시작/OOMKilled/CrashLoopBackOff 감지
- [x] 이상 감지 시 터미널에 경고 + `kubectl rollout undo` 명령 제안 출력
- [x] 시뮬레이션 클러스터에서 의도적 장애 배포 → 감지 데모 시나리오 동작 (kind 미설치로 시뮬레이터 대체)

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-14
- 원본 spec: deploy-soak-monitor.md
- 자동 생성: prototype-pipeline spawn
