# Deploy Soak Monitor

> 배포 후 자동 soak 윈도우 모니터링 — pod 상태/로그 실시간 감시로 이상 징후를 잡아내는 CLI 도구

## 실행 방법

```bash
# 의존성 설치
uv sync

# 사용 가능한 시나리오 목록
uv run python main.py scenarios

# 정상 배포 시나리오 (ALL CLEAR)
uv run python main.py watch default --scenario healthy --duration 15

# OOMKilled 장애 감지
uv run python main.py watch default --scenario oom --duration 15

# CrashLoopBackOff 장애 감지
uv run python main.py watch default --scenario crashloop --duration 20

# 에러 로그 패턴 감지 (panic, fatal, connection refused)
uv run python main.py watch production --scenario error_logs --duration 20
```

## 구조

```
deploy-soak-monitor/
├── main.py                 # 엔트리포인트
├── pyproject.toml          # 프로젝트 설정 (의존성 0개)
├── soak/
│   ├── __init__.py
│   ├── models.py           # Pod, Deployment, Event 데이터 모델
│   ├── cluster.py          # K8s 시뮬레이터 (4개 장애 시나리오)
│   ├── patterns.py         # 정규식 에러 패턴 매칭 (9개 패턴)
│   ├── reporter.py         # ANSI 컬러 터미널 출력
│   ├── monitor.py          # Soak 모니터 코어 로직
│   ├── demo.py             # 데모 시나리오 러너
│   └── cli.py              # CLI (argparse)
├── BUILD_LOG.md
├── STATUS.md
└── README.md
```

## 원본
prototype-pipeline spec: deploy-soak-monitor
