# AI Code Perf Verifier

> Git diff에서 변경된 Python 함수를 자동 식별하고, 변경 전/후 성능을 비교하여 머지 전 성능 회귀를 탐지하는 CLI 도구

## 실행 방법

```bash
# 의존성 설치
uv sync

# CLI 사용 (git 프로젝트 내에서)
uv run perf-verify                  # HEAD~1 대비 성능 비교
uv run perf-verify --list-only      # 변경 함수 목록만 출력
uv run perf-verify --threshold 3.0  # 3배 이상 느려질 때만 경고
uv run perf-verify --runs 10        # 벤치마크 10회 반복
uv run perf-verify --ref main       # main 브랜치 대비 비교

# End-to-end 데모
bash demo.sh
```

## 구조

```
├── perf_verify/
│   ├── cli.py            # CLI 진입점 (perf-verify 명령)
│   ├── diff_parser.py    # git diff 파싱 → 변경 파일/라인 추출
│   ├── ast_analyzer.py   # Python AST로 변경 함수/메서드 식별
│   ├── benchmarker.py    # 기존 테스트를 벤치마크로 실행 (시간/메모리)
│   └── reporter.py       # Rich 테이블 리포트 출력
├── sample_project/       # 데모용 샘플 프로젝트
│   ├── algorithms.py
│   └── tests/test_algorithms.py
├── demo.sh               # E2E 데모 스크립트
├── pyproject.toml
└── BUILD_LOG.md
```

## 원본
prototype-pipeline spec: ai-code-perf-verifier
