# Deploy Soak Monitor

> 배포 후 자동 soak 윈도우 모니터링 — pod 상태/로그 실시간 감시로 이상 징후를 잡아내는 CLI 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI (cli.py)                           │
│                   argparse: watch / scenarios                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ 명령 파싱
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Demo Runner (demo.py)                         │
│        시나리오 선택: healthy │ oom │ crashloop │ error_logs      │
└──────────────┬──────────────────────────────────┬────────────────┘
               │ create_deployment()              │ rolling_update()
               │ + 장애 주입                       │
               ▼                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                 Simulated Cluster (cluster.py)                   │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐    │
│  │ Deployment │──│    Pod     │──│  장애 주입 (inject_*)   │    │
│  │  생성/갱신  │  │  생성/삭제  │  │  OOM / CrashLoop / Log │    │
│  └────────────┘  └────────────┘  └─────────────────────────┘    │
│                                                                  │
│  Event 발행 ─────────────────────────────────────┐               │
└──────────────────────────────────────────────────┼───────────────┘
                                                   │ _emit() → watcher callback
                                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Soak Monitor (monitor.py)                      │
│                                                                  │
│  Event 수신 → Pod 상태 확인 ──┬── OOMKilled / BackOff 감지       │
│                               │                                  │
│                               └── 로그 분석 ─┐                   │
│                                              ▼                   │
│                              ┌──────────────────────────┐        │
│                              │ Pattern Matcher           │        │
│                              │ (patterns.py)             │        │
│                              │ 9개 정규식 패턴           │        │
│                              │ panic│fatal│oom│timeout…  │        │
│                              └──────────┬───────────────┘        │
│                                         │ PatternMatch           │
└─────────────────────────────────────────┼────────────────────────┘
                                          │ anomaly / pattern_alert
                                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Reporter (reporter.py)                       │
│                                                                  │
│  ANSI 터미널 출력:                                                │
│  ✓ Pod 시작  │  ↻ Rolling Update  │  ✖ 이상 징후  │  ⚠ Anomaly   │
│  Progress Bar [████░░░░] 40%  │  ALL CLEAR / SOAK FAILED        │
└──────────────────────────────────────────────────────────────────┘
```

## Demo

4가지 시나리오를 지원하며, K8s 클러스터 없이 시뮬레이션으로 동작합니다.

```bash
# 시나리오 목록 확인
$ uv run python main.py scenarios

Available demo scenarios:

  healthy      Normal deployment — no issues, soak completes with ALL CLEAR
  oom          Deployment where a pod gets OOMKilled after ~3 seconds
  crashloop    Deployment entering CrashLoopBackOff with 3 restarts
  error_logs   Deployment producing error logs (connection refused, panic, etc.)
```

### 정상 배포 (ALL CLEAR)

```bash
$ uv run python main.py watch default --scenario healthy --duration 15
```
```
════════════════════════════════════════════════════════════
  ☸ Soak Monitor
  Namespace: default | Window: 15s
════════════════════════════════════════════════════════════

  ✓ Pod web-api-1-xxxx started successfully
  ✓ Pod web-api-1-xxxx started successfully
  ↻ Deployment web-api updated to revision 2 (rolling update started)
  ✓ New pod web-api-2-xxxx started (revision 2)

  Soak progress: [██████████████████████████████] 100% (15s / 15s)

════════════════════════════════════════════════════════════
  ✅ ALL CLEAR — Soak window completed
  Pods monitored: 4
  Anomalies: 0
════════════════════════════════════════════════════════════
```

### OOMKilled 장애 감지

```bash
$ uv run python main.py watch default --scenario oom --duration 10
```
```
  ✓ New pod web-api-2-2959 started (revision 2)
  ✖ Pod web-api-2-2959 OOMKilled (memory limit exceeded)

  ────────────────────────────────────────────────────────
  ⚠  ANOMALY DETECTED
     Pod: web-api-2-2959
     Type: OOMKilled
     Detail: Container killed by OOM killer

     💡 Suggested rollback:
     $ kubectl rollout undo deployment/web-api -n default
  ────────────────────────────────────────────────────────

════════════════════════════════════════════════════════════
  ❌ SOAK FAILED — Issues detected
  Anomalies: 1
    1. OOMKilled: Container killed by OOM killer
════════════════════════════════════════════════════════════
```

### CrashLoopBackOff / Error Logs

```bash
# CrashLoopBackOff — 3회 재시작 후 감지
$ uv run python main.py watch default --scenario crashloop --duration 20

# 에러 로그 패턴 감지 (panic, fatal, connection refused 등)
$ uv run python main.py watch production --scenario error_logs --duration 20
```

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
