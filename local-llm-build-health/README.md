# Local LLM Build Health Advisor

> llama.cpp 릴리스 간 빌드·벤치마크 비교를 자동화하여 성능 회귀를 식별하는 CLI 도구

## Architecture

```
                        ┌─────────────────────┐
  CLI (cli.py)          │   build-health      │
  ─────────────────────▶│   compare / history  │
                        └────────┬────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
         ┌──────────┐   ┌──────────────┐  ┌──────────┐
         │ builder  │   │  benchmark   │  │ storage  │
         │          │   │              │  │          │
         │ git clone│   │ llama-bench  │  │ SQLite   │
         │ cmake    │   │ parse JSON   │  │ save/load│
         │ build    │   │ crash detect │  │          │
         └────┬─────┘   └──────┬───────┘  └────┬─────┘
              │                │               │
              └────────────────┴───────────────┘
                               │
                        ┌──────▼──────┐
                        │  display    │
                        │             │
                        │ rich tables │
                        │ ASCII chart │
                        │ crash report│
                        └─────────────┘
```

## Demo

### 두 릴리스 비교

```
$ uv run python cli.py compare b8580 b8583

═══ Processing b8580 ═══
Building b8580...
[builder] Build for b8580 already exists, reusing
Benchmarking b8580...
✓ b8580: 2 benchmark results

═══ Processing b8583 ═══
Building b8583...
[builder] Build for b8583 already exists, reusing
Benchmarking b8583...
✓ b8583: 2 benchmark results

    🔍 Benchmark Comparison: b8580 vs b8583
┏━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Metric       ┃ b8580 ┃ b8583 ┃         Delta ┃
┡━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━┩
│ Prompt tok/s │ 39.37 │ 37.99 │ -1.38 (-3.5%) │
│ Gen tok/s    │ 11.48 │ 11.75 │ +0.27 (+2.3%) │
│ Memory (MB)  │ 606.5 │ 606.5 │ +0.00 (+0.0%) │
└──────────────┴───────┴───────┴───────────────┘
```

### 벤치마크 히스토리

```
$ uv run python cli.py history

                        📊 Benchmark History
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Date       ┃ Tag   ┃ Model         ┃ PP tok/s ┃ TG tok/s ┃ Mem MB ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ 2026-03-30 │ b8583 │ llama 1B Q4_0 │    37.99 │    11.75 │  606.5 │
│ 2026-03-30 │ b8580 │ llama 1B Q4_0 │    39.37 │    11.48 │  606.5 │
└────────────┴───────┴───────────────┴──────────┴──────────┴────────┘

📈 Generation tok/s by Version

            b8580 │ ███████████████████████████████████████░ 11.48 tok/s
            b8583 │ ████████████████████████████████████████ 11.75 tok/s
```

### 크래시/에러 감지

```
$ uv run python cli.py compare b8580 nonexistent-tag

╭──────────────── Crash Report ────────────────╮
│ ⚠ BUILD/BENCH FAILURE for nonexistent-tag    │
│ Failed to clone tag 'nonexistent-tag'        │
│ — tag may not exist                          │
╰──────────────────────────────────────────────╯
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 두 릴리스 비교 (첫 실행 시 모델 ~600MB 자동 다운로드 + 빌드 ~5-10분)
uv run python cli.py compare b8580 b8583

# 벤치마크 히스토리 조회
uv run python cli.py history

# 커스텀 모델 사용
uv run python cli.py compare b8580 b8583 --model /path/to/model.gguf
```

**요구사항**: git, gcc, make (cmake는 자동 다운로드)

## 구조

```
local-llm-build-health/
├── cli.py          # CLI 엔트리포인트 (argparse)
├── builder.py      # llama.cpp 태그 clone + cmake 빌드
├── benchmark.py    # llama-bench 실행 + JSON 파싱
├── storage.py      # SQLite 저장/조회
├── display.py      # rich 테이블 + ASCII 차트
├── main.py         # 엔트리포인트 래퍼
├── pyproject.toml  # uv 프로젝트 설정
├── BUILD_LOG.md    # 빌드 일지
├── STATUS.md       # 프로토타입 상태
└── .work/          # (gitignored) 빌드 캐시, 모델
    ├── llama-{tag}/  # 태그별 소스 + 빌드
    └── models/       # GGUF 모델 파일
```

## 원본
prototype-pipeline spec: local-llm-build-health
