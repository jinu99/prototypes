# Proactive Alert Digest

> YAML 설정만으로 멀티소스 모니터링 → "오늘 아침에 뭘 봐야 하는지" 한 장짜리 다이제스트 생성

## Architecture

```
┌─────────────┐
│ digest.yaml │  YAML 설정 (소스 정의 + 출력 설정)
└──────┬──────┘
       │
       ▼
┌──────────────┐    ┌─────────────────┐
│   Engine     │───▶│  Plugin Registry │
│ (poll_all)   │    │                 │
└──────┬───────┘    │ ┌─────────────┐ │
       │            │ │ http_check  │ │
       │            │ │ log_pattern │ │
       │            │ │ docker_stat │ │
       │            │ │ prom_mock   │ │
       │            │ └─────────────┘ │
       │            └─────────────────┘
       │
       ▼
┌──────────────┐    ┌───────────────┐
│  Renderer    │───▶│ Jinja2 Template│
│ (severity    │    │ (digest.md.j2) │
│  sort+group) │    └───────────────┘
└──────┬───────┘
       │
       ├──▶ 📄 Markdown file
       └──▶ 📤 Slack webhook
```

## Demo

```bash
$ uv run python cli.py init
✅ Sample config written to digest.yaml

$ uv run python cli.py run
📋 Loading config from digest.yaml...
🔍 Polling 5 source(s)...
📝 Generating digest (7 alert(s))...
💾 Digest saved to digest_output.md
Done! ✨
```

생성되는 다이제스트 예시:

```markdown
# 🔔 Alert Digest — 2026-03-17 03:25

> **7** alerts: 2 critical · 2 warning · 0 info · 3 ok

## ⚡ 오늘 확인할 것
- 🔴 **Example API: Connection failed** — Cannot reach https://httpstat.us/500
- 🔴 **Prometheus Metrics: CPU usage > 90%** — Host server-01 CPU at 94%
- 🟡 **App Logs: 4 match(es) for 'ERROR|error|Error'** — Last match: ...
- 🟡 **Prometheus Metrics: Memory usage > 80%** — Host server-02 memory at 83%
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 샘플 설정 생성
uv run python cli.py init

# 다이제스트 실행
uv run python cli.py run

# Slack 전송 포함
uv run python cli.py run --slack

# 커스텀 설정 파일 사용
uv run python cli.py run -c my_config.yaml -o output.md
```

## 구조

```
proactive-alert-digest/
├── cli.py                 # Click CLI (init, run)
├── engine.py              # Config 로드 + 플러그인 폴링
├── models.py              # Alert, Severity, SourcePlugin Protocol
├── renderer.py            # Jinja2 마크다운 렌더러
├── slack.py               # Slack webhook 전송
├── sample_config.yaml     # 샘플 설정 파일
├── templates/
│   └── digest.md.j2       # 다이제스트 Jinja2 템플릿
├── plugins/
│   ├── __init__.py         # 플러그인 레지스트리
│   ├── http_check.py       # HTTP 헬스체크
│   ├── log_pattern.py      # 로그 파일 패턴 매칭
│   ├── docker_status.py    # Docker 컨테이너 상태
│   └── prometheus_mock.py  # Prometheus mock (확장 데모)
├── BUILD_LOG.md
├── STATUS.md
└── README.md
```

## 플러그인 추가 방법

1. `plugins/my_source.py`에 `poll() -> list[Alert]` 메서드가 있는 클래스 작성
2. `plugins/__init__.py`의 `PLUGIN_REGISTRY`에 등록
3. YAML 설정에 `type: my_source` 항목 추가

## 원본
prototype-pipeline spec: proactive-alert-digest
