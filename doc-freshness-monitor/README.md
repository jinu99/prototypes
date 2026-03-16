# Doc Freshness Monitor

> 코드 심볼 참조 기반으로 문서의 staleness를 감지하는 CLI 도구

## 실행 방법

```bash
# 의존성 설치
uv sync

# 문서에서 코드 심볼 참조 스캔
uv run doc-freshness scan <repo-path>

# staleness 점검 (Markdown 리포트)
uv run doc-freshness check <repo-path>

# 임계치 설정 (초과 시 exit code 1)
uv run doc-freshness check <repo-path> --threshold 50

# JSON 포맷 출력
uv run doc-freshness check <repo-path> --format json

# 파일로 저장
uv run doc-freshness check <repo-path> -o report.md
```

## 구조

```
doc_freshness/
  __init__.py
  cli.py               # CLI 엔트리포인트 (click)
  symbol_extractor.py   # 문서에서 코드 심볼 참조 추출
  git_tracker.py        # git log로 심볼 변경 이력 추적
  scorer.py             # staleness score (0-100) 산출
  reporter.py           # JSON/Markdown 리포트 생성
pyproject.toml
BUILD_LOG.md
STATUS.md
```

## 원본
prototype-pipeline spec: doc-freshness-monitor
