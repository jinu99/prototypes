# High-Privilege Dependency Scanner

> AST 기반 정적 분석으로 Python 의존성의 권한 수준을 스코어링하고 blast radius를 시각화하는 CLI 도구

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  Python Project  │     │  pipdeptree  │     │ site-packages│
│  (requirements   │────▶│  (dep graph) │     │  (.py files) │
│   .txt + venv)   │     └──────┬───────┘     └──────┬───────┘
└─────────────────┘            │                     │
                               ▼                     ▼
                    ┌──────────────────┐   ┌──────────────────┐
                    │   deps.py        │   │   analyzer.py    │
                    │   Dependency     │   │   AST Visitor    │
                    │   Graph Builder  │   │   Capability     │
                    │                  │   │   Detection      │
                    └────────┬─────────┘   └────────┬─────────┘
                             │                      │
                             ▼                      ▼
                    ┌────────────────────────────────┐
                    │          graph.py               │
                    │   Blast Radius Scoring          │
                    │   direct + propagated(decay)    │
                    │   + reverse_dep_bonus           │
                    └───────────────┬────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          ▼                   ▼
                 ┌──────────────┐    ┌──────────────┐
                 │  HTML Report │    │  JSON Output  │
                 │  (report.py) │    │               │
                 └──────────────┘    └──────────────┘
```

## Demo

LiteLLM 프로젝트(175개 패키지) 스캔 결과:

```
$ uv run python -m src.cli /tmp/litellm-test -n 10

[1/5] Finding Python environment in /tmp/litellm-test...
      Python: /tmp/litellm-test/.venv/bin/python
[2/5] Building dependency graph...
      Found 175 packages
      Direct dependencies from requirements.txt: 72
[3/5] Scanning packages for capabilities (AST analysis)...
      Scanned 173 packages (21205 files)
[4/5] Computing blast radius scores...
[5/5] Generating report...

✓ HTML report: /tmp/litellm-test/dep-privilege-report.html
  Completed in 140.7s

============================================================
 Top 10 High-Privilege Dependencies
============================================================
  #1  google-cloud-aiplatform (1.133.0)
      Blast Radius: 2044.6  |  Caps: code_exec, crypto, env_access, filesystem, network, process_exec
  #2  mcp (1.25.0)
      Blast Radius: 1116.9  |  Caps: code_exec, crypto, env_access, filesystem, network, process_exec
  #3  google-cloud-bigquery (3.40.1)
      Blast Radius: 996.5   |  Caps: code_exec, crypto, env_access, filesystem, network, process_exec
  #4  google-cloud-storage (3.10.1)
      Blast Radius: 911.8   |  Caps: code_exec, crypto, env_access, filesystem, network, process_exec
  #5  google-genai (1.37.0)
      Blast Radius: 814.1   |  Caps: code_exec, crypto, env_access, filesystem, network
```

HTML 리포트 예시: `example-report.html`

## 실행 방법

```bash
# 의존성 설치
uv sync

# 스캔 실행 (대상 프로젝트에 venv가 있어야 함)
uv run python -m src.cli /path/to/python/project

# 옵션
uv run python -m src.cli /path/to/project -n 10        # Top-10 하이라이트
uv run python -m src.cli /path/to/project --json        # JSON 출력
uv run python -m src.cli /path/to/project -o report.html  # 출력 경로 지정
```

## Blast Radius 공식

```
blast_radius = direct_score + propagated_score + reverse_dep_bonus

- direct_score: Σ(capability_weight × min(hit_count, 5))
- propagated_score: Σ(child_direct × 0.5^depth) — 감쇠 함수로 깊은 의존성일수록 영향 감소
- reverse_dep_bonus: ln(1 + reverse_dep_count) × 5 — 많은 패키지가 의존하면 폭발 반경 증가
```

### Capability 가중치

| Capability | Weight | 탐지 대상 |
|---|---|---|
| process_exec | 10 | subprocess, os.popen 등 |
| code_exec | 9 | eval, exec, ctypes 등 |
| network | 8 | socket, requests, httpx 등 |
| database | 7 | sqlite3, sqlalchemy 등 |
| env_access | 6 | os.environ, dotenv 등 |
| filesystem | 5 | open, shutil, pathlib 등 |
| crypto | 3 | cryptography, hashlib 등 |

## 구조

```
high-privilege-dep-scanner/
├── src/
│   ├── __init__.py
│   ├── cli.py          # CLI 진입점
│   ├── deps.py         # 의존성 추출 (pipdeptree, requirements.txt)
│   ├── analyzer.py     # AST 기반 capability 탐지
│   ├── graph.py        # 의존성 그래프 + blast radius 스코어링
│   └── report.py       # HTML 리포트 생성
├── example-report.html # LiteLLM 스캔 예시 리포트
├── BUILD_LOG.md        # 빌드 일지
├── STATUS.md           # 검증 결과
├── pyproject.toml
└── README.md
```

## 원본
prototype-pipeline spec: high-privilege-dep-scanner
