#!/bin/bash
# Fix Architecture sections in PRESENTATION.md — convert Korean to English
set -e

PROTO_BASE="/home/jinu/projects/prototypes"
CLAUDE="/home/jinu/.local/bin/claude"
LOG_DIR="/home/jinu/.claude/cron-logs"
DATE=$(date +%Y%m%d_%H%M)
LOG_FILE="${LOG_DIR}/proto-arch-english-${DATE}.log"
MAX_PARALLEL=10

mkdir -p "$LOG_DIR"
unset CLAUDECODE 2>/dev/null || true

log() { echo "$(date +%H:%M:%S): $*" | tee -a "$LOG_FILE"; }
log "=== Architecture English fix started ==="

TARGETS=()
for d in "$PROTO_BASE"/*/; do
  slug=$(basename "$d")
  [[ "$slug" == "scripts" || "$slug" == ".git" || "$slug" == "docs" ]] && continue
  [ -f "$d/PRESENTATION.md" ] || continue
  # Check if Architecture section has Korean
  if python3 -c "
import re, sys
text = open('$d/PRESENTATION.md').read()
m = re.search(r'## Architecture\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
if not m: sys.exit(1)
arch = re.sub(r'<!--.*?-->', '', m.group(1), flags=re.DOTALL)
if re.search(r'[\uac00-\ud7a3]', arch): sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    TARGETS+=("$slug")
  fi
done

log "Targets: ${#TARGETS[@]} prototypes with Korean in Architecture"

fix_one() {
  local slug="$1"
  local d="$PROTO_BASE/$slug"
  local slug_log="${LOG_DIR}/proto-arch-${slug}-${DATE}.log"

  PROMPT="$d/PRESENTATION.md 파일의 ## Architecture 섹션에서 한국어를 전부 영어로 바꿔줘.

## 규칙

1. ## Architecture 섹션 내부만 수정 (다른 섹션 절대 건드리지 마)
2. ASCII 다이어그램 안의 한국어 라벨 → 영어로 번역
3. 다이어그램 아래 설명 텍스트의 한국어 → 영어로 번역
4. 발표 스크립트(<!-- ... --> 안)는 한국어 유지 — 발표는 한국어니까
5. 다이어그램 구조(박스, 화살표, 정렬)는 절대 깨뜨리지 마
6. 기술 용어는 그대로 유지 (JSONL, AST, VRAM 등)
7. Edit 도구로 수정할 것

파일: $d/PRESENTATION.md"

  "$CLAUDE" -p "$PROMPT" \
    --permission-mode bypassPermissions \
    --no-session-persistence \
    --allowedTools "Read,Edit" \
    > "$slug_log" 2>&1
  local exit_code=$?

  if [ $exit_code -eq 0 ]; then
    # Verify Korean is gone from Architecture
    if python3 -c "
import re, sys
text = open('$d/PRESENTATION.md').read()
m = re.search(r'## Architecture\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
if not m: sys.exit(1)
arch = re.sub(r'<!--.*?-->', '', m.group(1), flags=re.DOTALL)
if re.search(r'[\uac00-\ud7a3]', arch): sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
      log "[OK] $slug"
      git -C "$PROTO_BASE" add "$slug/PRESENTATION.md" 2>/dev/null || true
    else
      log "[PARTIAL] $slug — some Korean remains"
      git -C "$PROTO_BASE" add "$slug/PRESENTATION.md" 2>/dev/null || true
    fi
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
    fix_one "${TARGETS[$j]}" &
    pids+=($!)
  done

  for pid in "${pids[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
  log "[BATCH $batch] Done"
done

# Commit
git -C "$PROTO_BASE" diff --cached --quiet 2>/dev/null || \
  git -C "$PROTO_BASE" commit -m "Convert Architecture sections to English in all presentations" >> "$LOG_FILE" 2>&1 || true

git -C "$PROTO_BASE" push >> "$LOG_FILE" 2>&1 || log "[WARN] git push failed"

ok=$(grep -c "\[OK\]" "$LOG_FILE" || echo 0)
partial=$(grep -c "\[PARTIAL\]" "$LOG_FILE" || echo 0)
fail=$(grep -c "\[FAIL\]" "$LOG_FILE" || echo 0)
log "=== Done: $ok fixed, $partial partial, $fail failed ==="
