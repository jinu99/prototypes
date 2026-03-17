#!/bin/bash
# Generate PRESENTATION.md for each prototype using Claude
# Parallel execution: 10 concurrent processes
set -e

PROTO_BASE="/home/jinu/projects/prototypes"
PIPELINE_BASE="/home/jinu/projects/prototype-pipeline"
CLAUDE="/home/jinu/.local/bin/claude"
LOG_DIR="/home/jinu/.claude/cron-logs"
DATE=$(date +%Y%m%d_%H%M)
LOG_FILE="${LOG_DIR}/proto-presentation-${DATE}.log"
MAX_PARALLEL=10

mkdir -p "$LOG_DIR"
unset CLAUDECODE 2>/dev/null || true

log() { echo "$(date +%H:%M:%S): $*" | tee -a "$LOG_FILE"; }
log "=== Presentation generation started (max $MAX_PARALLEL) ==="

# Collect targets
TARGETS=()
for d in "$PROTO_BASE"/*/; do
  slug=$(basename "$d")
  [[ "$slug" == "scripts" || "$slug" == ".git" || "$slug" == "docs" ]] && continue
  [ -f "$d/README.md" ] || continue
  # Skip if PRESENTATION.md already exists and is recent (> 100 lines)
  if [ -f "$d/PRESENTATION.md" ]; then
    lines=$(wc -l < "$d/PRESENTATION.md")
    [ "$lines" -gt 100 ] && continue
  fi
  TARGETS+=("$slug")
done

log "Targets: ${#TARGETS[@]} prototypes"

generate_one() {
  local slug="$1"
  local d="$PROTO_BASE/$slug"
  local slug_log="${LOG_DIR}/proto-pres-${slug}-${DATE}.log"

  # Gather context paths
  local idea_file="$PIPELINE_BASE/ideas/reviewed/${slug}.md"
  local spec_file="$PIPELINE_BASE/specs/built/${slug}.md"
  local build_log="$d/BUILD_LOG.md"
  local status_file="$d/STATUS.md"
  local readme_file="$d/README.md"

  PROMPT="이 프로토타입의 발표자료(PRESENTATION.md)를 만들어줘.

프로토타입 디렉토리: $d

## 참고할 파일들 (존재하는 것만 읽어)

1. README.md: $readme_file
2. BUILD_LOG.md: $build_log (구현 과정, 기술 판단)
3. STATUS.md: $status_file (완료 기준 결과)
4. 아이디어 원본: $idea_file (문제 정의, pain point 근거, 기존 솔루션)
5. Spec 문서: $spec_file (기술 범위, 심의 점수)
6. 소스 코드도 핵심 파일 2-3개 읽어서 실제 구현 파악

## 발표자료 구조 (Marp 마크다운)

8장 내외의 슬라이드로 구성:

### Slide 1: Title
- 프로토타입 제목, 한 줄 설명
- 카테고리, 기술 스택, 날짜

### Slide 2: Background
- 이 문제가 존재하는 배경 (개발자 생태계에서의 맥락)
- 왜 지금 이게 이슈인지
- idea 파일의 '문제' 섹션 참고

### Slide 3: Pain Point
- 커뮤니티에서 실제로 나온 고통
- pain point 근거 테이블 (출처, signal strength, 내용)
- idea 파일의 pain points 근거 테이블 활용

### Slide 4: Solution
- 우리 접근법 한 줄 요약
- 핵심 아이디어: 기존 솔루션과 뭐가 다른지
- spec의 검증 목표 활용

### Slide 5: Architecture
- README의 ASCII 다이어그램 그대로 활용
- 컴포넌트별 역할 한 줄 설명 추가

### Slide 6: Demo
- 실제 실행 결과 하이라이트 (README Demo 섹션 활용)
- 가장 인상적인 출력 1-2개만

### Slide 7: Key Decisions & Lessons
- BUILD_LOG에서 뽑은 핵심 기술 판단 2-3개
- 왜 이 스택을 골랐는지, 어떤 시행착오가 있었는지
- 심의 점수도 활용 (authenticity, prototypability 등)

### Slide 8: Results & Future
- STATUS.md 체크리스트 기반 성과 요약
- 한계점과 확장 방향
- 이 프로토타입이 실제 프로덕트가 되려면 뭐가 필요한지

## Marp 포맷 규칙

프론트매터:
\`\`\`
---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---
\`\`\`

슬라이드 구분: \`---\` (3개의 대시)

## 발표 스크립트 (가장 중요!)

**각 슬라이드 아래에 반드시 발표 스크립트를 넣어야 한다.**

Marp에서 발표자 노트 형식:
\`\`\`
<!--
여기에 발표 스크립트를 쓴다.
-->
\`\`\`

발표 스크립트는 진우의 말투로 작성한다. 진우의 말투 특징:

1. **관찰에서 시작해서 원리로 추상화**: '이런 현상이 있는데, 결국 이건 ... 문제다'
2. **현실적 메타포 사용**: '사람으로 치면...', '의사가 환자를 볼 때...'
3. **긴장감을 지적**: '빨리 하면 틀리고, 천천히 하면 늦다. 이 둘을 동시에 해결하는 게...'
4. **차분하고 담백한 톤**: 느낌표 금지, 과장 금지, '꽤', '결국', '마찬가지다' 같은 표현
5. **솔직한 한계 인정**: '솔직히 이건 좀 아쉬운데...', '완벽하진 않다'
6. **실용적 결론**: '그래서 이걸 왜 만들었냐면...'

예시 톤:
'커뮤니티에서 이런 얘기가 계속 나온다. AI 코딩 도구가 좋은데, 만든 코드가 다른 코드에 어떤 영향을 주는지 모른다는 거다. 결국 이건 변경 영향 추적 문제인데, 기존 IDE의 find references로는 부족하다. AST 레벨에서 봐야 한다.'

스크립트 분량: 슬라이드당 3-5문장. 실제로 입으로 말하는 느낌.

## 규칙

- 출력: $d/PRESENTATION.md 파일 하나만 생성
- 한국어 작성 (기술 용어만 영어)
- 기존 파일은 수정하지 말 것
- Write 도구로 PRESENTATION.md를 생성할 것
- 데이터가 없는 섹션은 합리적으로 추론해서 채울 것"

  "$CLAUDE" -p "$PROMPT" \
    --permission-mode bypassPermissions \
    --no-session-persistence \
    --allowedTools "Read,Write,Glob,Grep" \
    > "$slug_log" 2>&1
  local exit_code=$?

  if [ $exit_code -eq 0 ] && [ -f "$d/PRESENTATION.md" ]; then
    local lines=$(wc -l < "$d/PRESENTATION.md")
    if [ "$lines" -gt 50 ]; then
      log "[OK] $slug (${lines} lines)"
      git -C "$PROTO_BASE" add "$slug/PRESENTATION.md" 2>/dev/null || true
    else
      log "[WARN] $slug — PRESENTATION.md too short (${lines} lines)"
    fi
  else
    log "[FAIL] $slug (exit $exit_code)"
  fi
}

# Run in batches
total=${#TARGETS[@]}
batch=0
for ((i=0; i<total; i+=MAX_PARALLEL)); do
  batch=$((batch + 1))
  end=$((i + MAX_PARALLEL))
  [ $end -gt $total ] && end=$total
  log "[BATCH $batch] Starting: ${TARGETS[@]:i:MAX_PARALLEL}"

  pids=()
  for ((j=i; j<end; j++)); do
    generate_one "${TARGETS[$j]}" &
    pids+=($!)
  done

  for pid in "${pids[@]}"; do
    wait "$pid" 2>/dev/null || true
  done

  log "[BATCH $batch] Done"

  # Commit this batch
  git -C "$PROTO_BASE" diff --cached --quiet 2>/dev/null || \
    git -C "$PROTO_BASE" commit -m "Add presentations (batch $batch)" >> "$LOG_FILE" 2>&1 || true
done

# Push
git -C "$PROTO_BASE" push >> "$LOG_FILE" 2>&1 || log "[WARN] git push failed"

# Summary
ok=$(grep -c "\[OK\]" "$LOG_FILE" || echo 0)
fail=$(grep -c "\[FAIL\]" "$LOG_FILE" || echo 0)
warn=$(grep -c "\[WARN\]" "$LOG_FILE" || echo 0)
log "=== Done: $ok generated, $warn warnings, $fail failed ==="
