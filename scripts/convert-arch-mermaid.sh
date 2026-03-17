#!/bin/bash
# Convert ASCII Architecture diagrams to Mermaid in PRESENTATION.md
set -e

PROTO_BASE="/home/jinu/projects/prototypes"
CLAUDE="/home/jinu/.local/bin/claude"
LOG_DIR="/home/jinu/.claude/cron-logs"
DATE=$(date +%Y%m%d_%H%M)
LOG_FILE="${LOG_DIR}/proto-mermaid-${DATE}.log"
MAX_PARALLEL=10

mkdir -p "$LOG_DIR"
unset CLAUDECODE 2>/dev/null || true

log() { echo "$(date +%H:%M:%S): $*" | tee -a "$LOG_FILE"; }
log "=== Mermaid conversion started ==="

TARGETS=()
for d in "$PROTO_BASE"/*/; do
  slug=$(basename "$d")
  [[ "$slug" == "scripts" || "$slug" == ".git" || "$slug" == "docs" ]] && continue
  [ -f "$d/PRESENTATION.md" ] || continue
  # Only target files that still have ASCII code blocks (not mermaid) in Architecture
  if grep -q '## Architecture' "$d/PRESENTATION.md" && ! grep -q '```mermaid' "$d/PRESENTATION.md"; then
    TARGETS+=("$slug")
  fi
done

log "Targets: ${#TARGETS[@]} prototypes"

convert_one() {
  local slug="$1"
  local d="$PROTO_BASE/$slug"
  local slug_log="${LOG_DIR}/proto-mermaid-${slug}-${DATE}.log"

  PROMPT="$d/PRESENTATION.md 파일의 ## Architecture 섹션에서 ASCII 다이어그램을 Mermaid 다이어그램으로 교체해줘.

## 변환 규칙

1. ## Architecture 섹션 내부만 수정 (다른 섹션 절대 건드리지 마)
2. \`\`\` 코드블록을 \`\`\`mermaid 코드블록으로 교체
3. ASCII 박스/화살표 구조를 Mermaid graph 문법으로 변환
4. 방향: 보통 위→아래(TD) 또는 왼→오(LR). 데이터 파이프라인은 LR, 계층 구조는 TD가 자연스러움
5. 노드에 파일명이나 컴포넌트명을 포함: A[\"CLI (run.py)\"]
6. 엣지 라벨로 데이터 흐름 표시: A -->|\"SessionData\"| B
7. 관련 컴포넌트는 subgraph로 묶기
8. 발표 스크립트(<!-- ... --> 안)는 수정하지 마
9. 다이어그램 아래 설명 텍스트(bullet points)는 유지

## Mermaid 스타일 규칙

- 테마 설정은 넣지 마 (HTML에서 처리)
- 노드명은 영어로
- 따옴표 안에 파일명 포함: [\"Parser (parser.py)\"]
- subgraph 제목도 영어로

## 예시

변환 전:
\`\`\`
┌──────────┐     ┌──────────┐     ┌──────────┐
│   CLI    │────▶│  Parser  │────▶│ Analyzer │
└──────────┘     └──────────┘     └──────────┘
\`\`\`

변환 후:
\`\`\`mermaid
graph LR
    A[\"CLI (cli.py)\"] --> B[\"Parser (parser.py)\"]
    B --> C[\"Analyzer (analyzer.py)\"]
\`\`\`

## 주의사항

- Architecture 섹션의 코드블록만 교체. 다른 섹션의 코드블록(Demo 등)은 건드리지 마
- Edit 도구로 수정할 것
- 원본 ASCII의 구조(컴포넌트, 연결, 흐름 방향)를 정확히 보존할 것

파일: $d/PRESENTATION.md"

  "$CLAUDE" -p "$PROMPT" \
    --permission-mode bypassPermissions \
    --no-session-persistence \
    --allowedTools "Read,Edit" \
    > "$slug_log" 2>&1
  local exit_code=$?

  if [ $exit_code -eq 0 ] && grep -q '```mermaid' "$d/PRESENTATION.md" 2>/dev/null; then
    log "[OK] $slug"
    git -C "$PROTO_BASE" add "$slug/PRESENTATION.md" 2>/dev/null || true
  else
    log "[FAIL] $slug (exit $exit_code)"
  fi
}

total=${#TARGETS[@]}
batch=0
for ((i=0; i<total; i+=MAX_PARALLEL)); do
  batch=$((batch + 1))
  end=$((i + MAX_PARALLEL))
  [ $end -gt $total ] && end=$total
  log "[BATCH $batch] Starting: ${TARGETS[@]:i:MAX_PARALLEL}"

  pids=()
  for ((j=i; j<end; j++)); do
    convert_one "${TARGETS[$j]}" &
    pids+=($!)
  done

  for pid in "${pids[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
  log "[BATCH $batch] Done"
done

# Commit & push
git -C "$PROTO_BASE" diff --cached --quiet 2>/dev/null || \
  git -C "$PROTO_BASE" commit -m "Convert Architecture diagrams from ASCII to Mermaid" >> "$LOG_FILE" 2>&1 || true
git -C "$PROTO_BASE" push >> "$LOG_FILE" 2>&1 || log "[WARN] git push failed"

ok=$(grep -c "\[OK\]" "$LOG_FILE" || echo 0)
fail=$(grep -c "\[FAIL\]" "$LOG_FILE" || echo 0)
log "=== Done: $ok converted, $fail failed ==="
