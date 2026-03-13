# Embedding Migration Guard

> CLI 도구로 임베딩 모델 교체 전 recall@k 드롭을 예측하여, 전체 재인덱싱 없이 마이그레이션 의사결정을 내릴 수 있게 합니다.

## 실행 방법

```bash
# 의존성 설치
uv sync

# 데모 실행 (내장 110개 문서 코퍼스, all-MiniLM-L6-v2 vs all-MiniLM-L12-v2)
uv run emg demo

# 커스텀 코퍼스로 두 모델 비교
uv run emg check --old all-MiniLM-L6-v2 --new all-MiniLM-L12-v2 --corpus corpus.txt

# JSON 리포트 저장
uv run emg check --old all-MiniLM-L6-v2 --new all-MiniLM-L12-v2 --corpus corpus.txt --output report.json

# recall@k 값 커스텀
uv run emg check --old all-MiniLM-L6-v2 --new all-MiniLM-L12-v2 --corpus corpus.txt --k 1,3,5,10,20
```

코퍼스 파일은 한 줄에 문서 하나, 또는 `.txt` 파일들이 담긴 디렉토리를 지정할 수 있습니다.

## 구조

```
embedding-migration-guard/
├── emg/
│   ├── __init__.py          # 패키지 초기화
│   ├── cli.py               # Click CLI (check, demo 서브커맨드)
│   ├── comparator.py        # 벡터 공간 비교 (cosine, NN overlap, recall@k)
│   ├── embedder.py          # 모델 로딩 및 임베딩 생성
│   ├── report.py            # 콘솔 출력 및 JSON export
│   └── sample_corpus.py     # 내장 샘플 코퍼스 (110개 문서)
├── pyproject.toml           # 프로젝트 설정 및 의존성
├── BUILD_LOG.md             # 빌드 일지
├── STATUS.md                # 검증 결과
└── README.md                # 이 파일
```

## 원본
prototype-pipeline spec: embedding-migration-guard
