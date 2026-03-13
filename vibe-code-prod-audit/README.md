# vibe-audit

> tree-sitter 기반 바이브코딩 FastAPI 프로젝트 프로덕션 준비도 감사 CLI 도구

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
