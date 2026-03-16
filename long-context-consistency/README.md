# Long Context Consistency

> 장편 텍스트에서 사실을 추출하고, 임베딩 유사도 기반으로 잠재적 불일치를 탐지하는 CLI 도구

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLI (cli.py)                               │
│         Click 기반 커맨드: init / extract / check / context         │
└──────┬──────────┬───────────────┬───────────────┬───────────────────┘
       │          │               │               │
       ▼          ▼               ▼               ▼
┌──────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  init    │ │   extract    │ │    check     │ │     context      │
│          │ │              │ │              │ │                  │
│ DB 초기화 │ │ 사실 추출 +  │ │ 신규 사실 vs │ │ scene 텍스트에   │
│          │ │ 임베딩 저장   │ │ 기존 DB 비교  │ │ 관련 사실 선별   │
└──────────┘ └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘
                    │                │                   │
       ┌────────────┘                │                   │
       ▼                             ▼                   ▼
┌──────────────┐            ┌──────────────┐    ┌──────────────────┐
│ extractor.py │            │  checker.py  │    │   context.py     │
│              │            │              │    │                  │
│ Regex 패턴   │──사실들──▶ │ Phase 1:     │    │ scene 임베딩 생성 │
│ 매칭으로     │            │  동일 엔티티  │    │       │          │
│ Fact 추출    │            │  속성값 비교  │    │       ▼          │
│              │            │ Phase 2:     │    │ 코사인 유사도로   │
│ 패턴 종류:   │            │  임베딩 유사도│    │ 관련 사실 랭킹    │
│ ├ 외모 묘사  │            │  교차 비교   │    │       │          │
│ ├ 위치/거주지│            │              │    │       ▼          │
│ ├ 관계       │            │ Inconsistency│    │ 토큰 예산 내     │
│ └ 나이       │            │ 리포트 생성  │    │ 스니펫 패킹      │
└──────┬───────┘            └──────┬───────┘    └────────┬─────────┘
       │                           │                     │
       ▼                           ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                         db.py (SQLite)                          │
│                                                                 │
│  .consistency.db                                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ facts 테이블                                            │    │
│  │ id │ entity │ attribute │ value │ source │ chapter │ …  │    │
│  │    │        │           │       │        │         │emb │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  sentence-transformers (all-MiniLM-L6-v2) 로 임베딩 생성        │
└─────────────────────────────────────────────────────────────────┘
```

**데이터 흐름 요약:**
1. `extract` — 텍스트 파일 → Regex 패턴 매칭 → `Fact` 추출 → 임베딩 생성 → SQLite 저장
2. `check` — 신규 텍스트에서 사실 추출 → 기존 DB의 사실과 (속성 직접 비교 + 임베딩 유사도) 이중 검사 → 불일치 리포트
3. `context` — scene 텍스트 임베딩 → DB 내 사실들과 유사도 랭킹 → 토큰 예산 내 관련 사실 스니펫 생성

## Demo

```bash
# 1. 프로젝트 초기화
$ uv run consistency init sample_data
✓ Initialized consistency DB at /path/to/sample_data
  Database: /path/to/sample_data/.consistency.db
  Existing facts: 0

# 2. 챕터 1에서 사실 추출
$ uv run consistency extract sample_data/chapter1.txt -d sample_data
Extracting facts from chapter1.txt...
Embedding 8 facts...

✓ Extracted 8 facts from chapter1.txt
  Total facts in DB: 8

  [Chapter 1] Elena.eye_color = deep green
  [Chapter 1] Elena.hair = long dark
  [Chapter 1] Elena.occupation = a scholar
  [Chapter 1] Elena.location = Ashford
  [Chapter 1] Marcus.has_brother = Elena
  ...

# 3. 챕터 2 추출 (의도적 모순 포함)
$ uv run consistency extract sample_data/chapter2.txt -d sample_data
Extracting facts from chapter2.txt...
Embedding 6 facts...

✓ Extracted 6 facts from chapter2.txt
  Total facts in DB: 14

# 4. 챕터 3으로 불일치 검사
$ uv run consistency check sample_data/chapter3.txt -d sample_data
Extracting facts from chapter3.txt...
Embedding 5 new facts...
Checking for inconsistencies...

⚠ Found 3 potential inconsistencies:

⚠ INCONSISTENCY: Elena.eye_color changed: 'deep green' → 'bright blue'
  Fact A: Elena.eye_color = deep green (file=chapter1.txt, Chapter 1, line 5)
    → "Elena had deep green eyes that sparkled in the sunlight"
  Fact B: Elena.eye_color = bright blue (file=chapter3.txt, Chapter 3, line 12)
    → "Elena had bright blue eyes, unchanged since childhood"
  Similarity: 0.847

# 5. 컨텍스트 스니펫 생성 (토큰 예산 1000)
$ uv run consistency context sample_data/chapter3.txt -d sample_data -b 1000
## Relevant Facts for Current Scene

_Token budget: 1000, used: ~320_

- **Elena**.eye_color = deep green  _(from Chapter 1, line 5)_
- **Elena**.hair = long dark  _(from Chapter 1, line 7)_
- **Elena**.location = Ashford  _(from Chapter 1, line 15)_
- **Marcus**.has_brother = Elena  _(from Chapter 1, line 22)_

_(4 facts selected, 2 entities)_

# 6. JSON 출력 모드
$ uv run consistency check sample_data/chapter3.txt -d sample_data -j
[
  {
    "fact_a": {
      "entity": "Elena",
      "attribute": "eye_color",
      "value": "deep green",
      "source_file": "chapter1.txt",
      "chapter": "Chapter 1",
      ...
    },
    "fact_b": { ... },
    "similarity": 0.847,
    "reason": "Elena.eye_color changed: 'deep green' → 'bright blue'"
  }
]
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 프로젝트 초기화
uv run consistency init sample_data

# 사실 추출 (챕터별)
uv run consistency extract sample_data/chapter1.txt -d sample_data
uv run consistency extract sample_data/chapter2.txt -d sample_data

# 불일치 검사
uv run consistency check sample_data/chapter3.txt -d sample_data

# 컨텍스트 스니펫 생성
uv run consistency context sample_data/chapter3.txt -d sample_data -b 1000
```

## 주요 옵션

```
consistency extract <file> -d <dir> -j    # JSON 출력
consistency check <file> -d <dir> -t 0.5  # 임계값 조정
consistency context <scene> -d <dir> -b 2000  # 토큰 예산 설정
```

## 구조

```
consistency/
├── cli.py          # Click CLI 인터페이스
├── db.py           # SQLite 사실 DB (Fact dataclass + CRUD)
├── extractor.py    # 규칙 기반 사실 추출 (regex 패턴)
├── checker.py      # 임베딩 기반 불일치 탐지 (sentence-transformers)
└── context.py      # 토큰 예산 내 컨텍스트 스니펫 생성
sample_data/
├── chapter1.txt    # 샘플 소설 챕터 1
├── chapter2.txt    # 샘플 소설 챕터 2 (Elena 눈 색깔 모순 포함)
└── chapter3.txt    # 샘플 소설 챕터 3 (의도적 모순 5건 포함)
```

## 원본
prototype-pipeline spec: long-context-consistency
