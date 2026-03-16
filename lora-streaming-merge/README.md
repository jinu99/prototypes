# LoRA Streaming Merge

> 16GB RAM 환경에서 safetensors lazy loading을 활용한 텐서 단위 스트리밍 LoRA 머지 CLI

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  Base Model      │     │  LoRA Adapter     │
│  (multi-shard    │     │  adapter_model    │
│   safetensors)   │     │  .safetensors     │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         ▼                       ▼
┌────────────────────────────────────────────┐
│            shard_map.py                    │
│  model.safetensors.index.json → key→shard  │
└────────────────┬───────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────┐
│            adapter.py                      │
│  adapter_config.json parsing               │
│  LoRA key → base key mapping               │
└────────────────┬───────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────┐
│            merge.py (streaming)            │
│  for each tensor:                          │
│    W = safe_open.get_tensor(key)           │
│    if LoRA target:                         │
│      A, B = adapter.get_tensor(...)        │
│      W' = W + (alpha/r) * B @ A            │
│    save_file({key: W'}, shard_N)           │
│    del W, A, B  ← memory freed            │
└────────────────┬───────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────┐
│  Output: merged safetensors shards         │
│  + model.safetensors.index.json            │
└────────────────────────────────────────────┘
```

## Demo

### Merge 실행
```
$ lora-merge run --base tests/fixtures/base_model --adapter tests/fixtures/adapter --output /tmp/merged
Merging: 100%|██████████| 30/30 [00:00<00:00, 1423.83it/s]

Done! Merged 24/30 tensors → 30 shards
Peak RAM:      0.2 MB
Output size:   0.7 MB
RAM savings:   64% vs full load
Output:        /tmp/merged
```

### Estimate 리포트
```
$ lora-merge estimate --base tests/fixtures/base_model --adapter tests/fixtures/adapter
═══ LoRA Merge Estimation Report ═══

  Base model:    2 shard(s), 30 tensors
  LoRA targets:  24 tensors (rank=8, alpha=16, scaling=2.00)
  Batch size:    1 tensor(s) per output shard

─── Source Shards ───
  model-00001-of-00002.safetensors: 15 tensors, 0.3 MB
  model-00002-of-00002.safetensors: 15 tensors, 0.3 MB

─── Resource Estimate ───
  Peak RAM (streaming):  0.07 MB
  Full model in-memory:  0.7 MB
  Total disk output:     0.7 MB
  Estimated time:        0.0s

  ★ Memory savings: 90% vs full load
═══════════════════════════════════
```

### 정밀도 검증
```
$ lora-merge run --base tests/fixtures/base_model --adapter tests/fixtures/adapter --output /tmp/merged --verify
...
✓ All tensors match (rtol=1e-5)
```

### 메모리 절약 증명 (32레이어 모델)
```
Full model:    82.0 MB
Peak RAM:      1.40 MB (1.7%)
1/N threshold: 2.56 MB (N=32)
Result:        PASS
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 테스트 픽스처 생성
uv run python tests/create_fixtures.py

# 머지 실행
uv run lora-merge run --base tests/fixtures/base_model --adapter tests/fixtures/adapter --output /tmp/merged

# 리소스 예측
uv run lora-merge estimate --base tests/fixtures/base_model --adapter tests/fixtures/adapter

# 정밀도 검증 포함 머지
uv run lora-merge run --base tests/fixtures/base_model --adapter tests/fixtures/adapter --output /tmp/merged --verify

# 독립 검증
uv run lora-merge verify --base tests/fixtures/base_model --adapter tests/fixtures/adapter --output /tmp/merged
```

## 구조

```
lora-streaming-merge/
├── src/
│   ├── __init__.py
│   ├── cli.py          # CLI entry point (run, estimate, verify)
│   ├── merge.py        # Core streaming merge logic
│   ├── shard_map.py    # Multi-file shard → key mapping
│   ├── adapter.py      # adapter_config.json parsing & key mapping
│   ├── estimate.py     # Pre-merge resource estimation
│   └── verify.py       # Precision verification (naive merge comparison)
├── tests/
│   ├── create_fixtures.py  # Generate fake model + adapter
│   └── fixtures/           # Generated test data
├── BUILD_LOG.md
├── STATUS.md
├── README.md
└── pyproject.toml
```

## 원본
prototype-pipeline spec: lora-streaming-merge
