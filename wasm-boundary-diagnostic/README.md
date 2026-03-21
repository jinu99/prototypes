# WASM Boundary Diagnostic

> wasm-bindgen 글루 코드의 정적 분석으로 JS↔WASM 경계 함수의 직렬화 비용을 자동 식별하고 최적화를 추천하는 CLI 도구

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  _bg.js 글루코드  │────▶│   Parser     │────▶│  Cost Model  │────▶│  Recommender │
│  (wasm-bindgen)  │     │ (regex 패턴)  │     │ (타입→등급)   │     │ (5가지 패턴)  │
└─────────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                              │                     │                     │
                              ▼                     ▼                     ▼
                        BoundaryFunction      FunctionCost         Recommendation
                        - name, kind          - overall level      - pattern
                        - params[]            - param costs[]      - title
                        - return_type         - total score        - description
                              │                     │                     │
                              └─────────────────────┴─────────────────────┘
                                                    │
                                              ┌─────▼─────┐
                                              │  Reporter  │
                                              │  (Rich)    │
                                              └─────┬─────┘
                                                    │
                                          ┌─────────┴─────────┐
                                          ▼                   ▼
                                    Terminal Report      JSON Output
```

## Demo

```
$ wasm-diag samples/image_processor_bg.js --min-cost high

╭──────────────────────────────────────────────────╮
│ WASM Boundary Diagnostic Report                  │
│ samples/image_processor_bg.js                    │
╰──────────────────────────────────────────────────╯

 Boundary Functions (sorted by cost)
┏━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃  Cost   ┃ Score ┃ Kind   ┃ Function         ┃ Parameters        ┃ Return┃
┡━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ ■ high  │    30 │ export │ convert_format   │ string, string,   │ bytes │
│         │       │        │                  │ bytes             │       │
│ ■ high  │    17 │ export │ process_image    │ string, bytes     │ jsval │
│ ■ high  │    16 │ export │ batch_process    │ jsvalue_array,    │ jsval │
│         │       │        │                  │ jsvalue           │       │
└─────────┴───────┴────────┴──────────────────┴───────────────────┴───────┘

 Optimization Recommendations
  1. Use Opaque Handle Instead of Serialization
     Affected: convert_format, process_image
  2. Use serde-wasm-bindgen for Structured Data
     Affected: convert_format, process_image
  3. Batch Multiple Calls into One Boundary Crossing
     Affected: convert_format, process_image, batch_process
```

JSON 출력도 지원:
```
$ wasm-diag samples/image_processor_bg.js --json
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행
uv run wasm-diag <path-to-_bg.js>

# 옵션
uv run wasm-diag samples/image_processor_bg.js                  # 전체 리포트
uv run wasm-diag samples/image_processor_bg.js --min-cost high  # high 이상만
uv run wasm-diag samples/image_processor_bg.js --json           # JSON 출력
```

## 구조

```
wasm-boundary-diagnostic/
├── src/
│   ├── __init__.py
│   ├── cli.py           # CLI 엔트리포인트 (click)
│   ├── parser.py        # _bg.js 파싱, 경계 함수/타입 추출
│   ├── cost_model.py    # 타입별 직렬화 비용 모델
│   ├── recommender.py   # 최적화 추천 엔진 (5가지 패턴)
│   └── report.py        # Rich 터미널 리포트 렌더러
├── samples/
│   └── image_processor_bg.js  # 샘플 wasm-bindgen 글루 코드
├── pyproject.toml
├── BUILD_LOG.md
└── STATUS.md
```

## 원본
prototype-pipeline spec: wasm-boundary-diagnostic
