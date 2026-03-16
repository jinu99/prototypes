# Embedding Migration Guard

> CLI 도구로 임베딩 모델 교체 전 recall@k 드롭을 예측하여, 전체 재인덱싱 없이 마이그레이션 의사결정을 내릴 수 있게 합니다.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                            │
│              check / demo 서브커맨드 (Click)                      │
└──────────┬──────────────────────────────────┬───────────────────┘
           │                                  │
           ▼                                  ▼
┌─────────────────────┐            ┌─────────────────────────┐
│   Corpus Loader     │            │   Model Loader          │
│   (embedder.py)     │            │   (embedder.py)         │
│                     │            │                         │
│ • 텍스트 파일 로드    │            │ • SentenceTransformer   │
│ • 디렉토리 스캔      │            │   모델 2개 로드 (old/new)│
└────────┬────────────┘            └────────┬────────────────┘
         │ texts                            │ old_model, new_model
         ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Embedding 생성 (embedder.py)                  │
│          embed_texts() → L2 정규화된 (n, dim) ndarray            │
└──────────┬────────────────────────────────┬─────────────────────┘
           │ old_emb                        │ new_emb
           ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Comparator (comparator.py)                      │
│                                                                  │
│  ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────┐  │
│  │ Pairwise Cosine  │ │ NN Overlap       │ │ Recall@K        │  │
│  │ Similarity       │ │ (Jaccard)        │ │                 │  │
│  │                  │ │                  │ │ query별 old/new  │  │
│  │ old[i]↔new[i]   │ │ top-k 이웃 비교   │ │ top-k 결과 비교  │  │
│  └────────┬─────────┘ └────────┬─────────┘ └───────┬─────────┘  │
│           │                    │                    │             │
└───────────┼────────────────────┼────────────────────┼─────────────┘
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Report (report.py)                           │
│                                                                  │
│  • Risk 판정: recall@10 + NN overlap 기반 (LOW/MEDIUM/HIGH)      │
│  • 콘솔 리포트 출력 (print_report)                                │
│  • JSON 파일 export (export_json)                                │
└─────────────────────────────────────────────────────────────────┘
```

## Demo

`uv run emg demo` 실행 시, 내장 110개 문서 코퍼스로 `all-MiniLM-L6-v2` → `all-MiniLM-L12-v2` 마이그레이션을 시뮬레이션합니다.

```bash
$ uv run emg demo

  EMG Demo — comparing all-MiniLM-L6-v2 vs all-MiniLM-L12-v2
  Corpus: 110 built-in sample documents
  Queries: 22 sample queries
  Loading old model: all-MiniLM-L6-v2
  Loading new model: all-MiniLM-L12-v2
  Embedding 110 documents with old model...
  Embedding 110 documents with new model...
  Computing pairwise cosine similarities...
  Computing nearest-neighbor overlap (k=10)...
  Computing recall@k with 22 queries...

============================================================
  EMBEDDING MIGRATION GUARD — COMPARISON REPORT
============================================================

  Old model : all-MiniLM-L6-v2
  New model : all-MiniLM-L12-v2
  Documents : 110

────────────────────────────────────────────────────────────
  DIMENSIONS
────────────────────────────────────────────────────────────
  Old: 384   New: 384   Match: ✓

────────────────────────────────────────────────────────────
  COSINE SIMILARITY (old ↔ new, per document)
────────────────────────────────────────────────────────────
  Mean: 0.5566   Std: 0.0571
  Min:  0.3596   Max: 0.6655

────────────────────────────────────────────────────────────
  NEAREST-NEIGHBOR OVERLAP (k=10)
────────────────────────────────────────────────────────────
  Mean Jaccard: 0.6070   Std: 0.1569

────────────────────────────────────────────────────────────
  RECALL@K
────────────────────────────────────────────────────────────
  recall@1:  mean=0.5000  std=0.5000
  recall@5:  mean=0.7364  std=0.1639
  recall@10: mean=0.7955  std=0.0976

────────────────────────────────────────────────────────────
  RISK: 🟡 MEDIUM
────────────────────────────────────────────────────────────
  Migration has moderate risk. Some recall degradation expected.
  Consider testing with production queries.
============================================================
```

커스텀 코퍼스로 비교하려면:

```bash
$ uv run emg check --old all-MiniLM-L6-v2 --new all-MiniLM-L12-v2 \
    --corpus my_docs.txt --k 1,5,10,20 --output report.json
```

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
