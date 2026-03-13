# Long Context Consistency

> 장편 텍스트에서 사실을 추출하고, 임베딩 유사도 기반으로 잠재적 불일치를 탐지하는 CLI 도구

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
