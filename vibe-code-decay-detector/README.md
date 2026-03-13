# Vibe Code Decay Detector

> Git 히스토리 기반 아키텍처 침식 탐지 CLI — 의존성 결합도, 순환 의존성, churn rate 추적 및 commit-revert 패턴 감지

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행
uv run decay-detect scan <repo-path>

# 옵션
uv run decay-detect scan <repo-path> --max-commits 200 --db metrics.db
```

## 테스트

```bash
# 테스트 repo 생성
bash create_test_repo.sh

# 분석 실행
uv run decay-detect scan /tmp/decay-test-repo
```

## 구조

```
decay_detect/
├── __init__.py
├── cli.py                 # Click CLI 엔트리포인트
├── git_analyzer.py        # Git 히스토리 분석 (커밋 목록, 파일 내용, churn)
├── dependency_parser.py   # tree-sitter 기반 import 파싱 (Python, JS)
├── metrics.py             # 의존성 그래프 메트릭 (edge count, 순환 의존성)
├── pattern_detector.py    # commit-revert 패턴 감지 (add-delete, rapid-edit)
├── visualizer.py          # Rich 터미널 차트 및 경고 출력
└── storage.py             # SQLite 시계열 저장
```

## 원본
prototype-pipeline spec: vibe-code-decay-detector
