# vibe-audit

> tree-sitter 기반 바이브코딩 FastAPI 프로젝트 프로덕션 준비도 감사 CLI 도구

## Architecture

```
┌─────────────────┐
│   CLI (cli.py)  │  argparse: scan <project-dir> [--json] [--output-dir]
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              Scanner (scanner.py)                    │
│                                                     │
│  project-dir ──▶ find_python_files()                │
│                       │                             │
│                       ▼                             │
│              tree-sitter Parser                     │
│                       │                             │
│          ┌────────────┼────────────┐                │
│          ▼            ▼            ▼                │
│    Route 추출    Middleware    Error Handler         │
│   (@app.get,     검출         검출                  │
│    @router.post)                                    │
│          │            │            │                │
│          └────────────┼────────────┘                │
│                       ▼                             │
│               ScanResult 생성                       │
│  (routes, has_healthcheck, has_cors, test_files...) │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│           Checklist (checklist.py)                   │
│                                                     │
│  fastapi_checklist.json                             │
│       │                                             │
│       ▼                                             │
│  9개 항목 평가 (가중치 기반 점수화)                 │
│  ┌──────────┬──────────┬──────────┬──────────┐      │
│  │Structure │Reliability│ Quality │ Security │      │
│  │ (20)     │  (35)    │  (20)   │  (20)    │      │
│  └──────────┴──────────┴──────────┴──────────┘      │
│       │                                             │
│       ▼                                             │
│  AuditReport { score: 0-100, items[], scan }        │
└───────────────────────┬─────────────────────────────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
┌──────────────────┐  ┌────────────────────────┐
│  Terminal 리포트  │  │  Generator (generator.py)│
│  (컬러 바, 체크  │  │                          │
│   리스트, 라우트) │  │  실패 항목별 보완 코드:  │
│                  │  │  ├─ health.py             │
│  또는 --json     │  │  ├─ test_api.py           │
│  JSON 출력       │  │  ├─ Dockerfile            │
│                  │  │  ├─ error_handlers.py      │
└──────────────────┘  │  └─ config.py             │
                      └────────────────────────────┘
```

## Demo

```bash
# 미완성 프로젝트 스캔 (프로덕션 준비도가 낮은 프로젝트)
$ uv run vibe-audit scan sample_project

🔍 Scanning: /path/to/sample_project

   Found 2 Python file(s), 3 route(s)

──────────────────────────────────────────────────
  Production Readiness Score
  ██████░░░░░░░░░░░░░░░░░░░░░░░░  10/100
──────────────────────────────────────────────────

  📡 Routes (3):
   GET     /              ← main.py:8
   GET     /users         ← main.py:13
   POST    /users         ← main.py:18

  📋 Checklist:

   Structure
    ✓ Route Definitions (w:10)
      3 route(s) detected
    ✗ Middleware (w:5)
      No middleware configured
    ✗ Dependency Management (w:5)
      No dependency file (requirements.txt or pyproject.toml)

   Reliability
    ✗ Health Check Endpoint (w:20)
      No health check endpoint (/health, /healthz, /ping)
    ✗ Error Handling (w:15)
      No exception handlers or try/except blocks in route handlers

   Quality
    ✗ Test Files (w:20)
      No test files found (test_*.py or *_test.py)

   Security
    ✗ Environment Variable Management (w:15)
      No environment variable management (os.environ, dotenv, BaseSettings)
    ✗ CORS Configuration (w:5)
      No CORS configuration found

   Deployment
    ✗ Dockerfile (w:5)
      No Dockerfile found

🔧 Generating remediation code...

   ✓ generated/health.py
   ✓ generated/test_api.py
   ✓ generated/Dockerfile
   ✓ generated/error_handlers.py
   ✓ generated/config.py
```

```bash
# JSON 출력 모드 (CI/CD 파이프라인 연동 시 활용)
$ uv run vibe-audit scan sample_project --json
{
  "score": 10,
  "routes": [
    {"method": "GET", "path": "/", "function": "root", "file": "main.py", "line": 8}
  ],
  "checks": [
    {"id": "has_routes", "name": "Route Definitions", "category": "structure", "passed": true, ...},
    {"id": "has_healthcheck", "name": "Health Check Endpoint", "category": "reliability", "passed": false, ...}
  ]
}
```

```bash
# 잘 갖춰진 프로젝트 스캔 (높은 점수)
$ uv run vibe-audit scan sample_project_good

🔍 Scanning: /path/to/sample_project_good

   Found 4 Python file(s), 5 route(s)

──────────────────────────────────────────────────
  Production Readiness Score
  ████████████████████████████░░  95/100
──────────────────────────────────────────────────

✨ All checks passed! Your project is production-ready.
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 스캔 실행
uv run vibe-audit scan <project-dir>

# JSON 출력
uv run vibe-audit scan <project-dir> --json

# 보완 코드 출력 디렉토리 지정
uv run vibe-audit scan <project-dir> --output-dir ./remediation
```

## 데모

```bash
# 미완성 프로젝트 스캔 (10/100)
uv run vibe-audit scan sample_project

# 잘 갖춰진 프로젝트 스캔 (95/100)
uv run vibe-audit scan sample_project_good
```

## 체크리스트 항목

| 항목 | 카테고리 | 가중치 |
|------|----------|--------|
| Route Definitions | Structure | 10 |
| Health Check Endpoint | Reliability | 20 |
| Test Files | Quality | 20 |
| Error Handling | Reliability | 15 |
| Environment Variable Management | Security | 15 |
| Middleware | Structure | 5 |
| CORS Configuration | Security | 5 |
| Dockerfile | Deployment | 5 |
| Dependency Management | Structure | 5 |

## 구조

```
vibe-code-prod-audit/
├── vibe_audit/
│   ├── __init__.py          # 패키지 초기화
│   ├── cli.py               # CLI 인터페이스 (argparse)
│   ├── scanner.py           # tree-sitter 기반 FastAPI 스캐너
│   ├── checklist.py         # 체크리스트 점수화 로직
│   └── generator.py         # 보완 코드 생성기
├── fastapi_checklist.json   # 체크리스트 정의 (JSON)
├── sample_project/          # 테스트용 미완성 FastAPI 프로젝트
├── sample_project_good/     # 테스트용 잘 갖춰진 FastAPI 프로젝트
├── pyproject.toml
├── BUILD_LOG.md
└── STATUS.md
```

## 원본
prototype-pipeline spec: vibe-code-prod-audit
