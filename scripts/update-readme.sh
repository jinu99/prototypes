#!/bin/bash
# Regenerate root README.md from prototype directories
# Called by spawn.sh after successful prototype creation

set -e
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# --- Collect prototype data ---
declare -A DESCS STACKS CATEGORIES

for d in */; do
  [ -d "$d" ] || continue
  slug="${d%/}"
  [[ "$slug" == "scripts" || "$slug" == ".git" ]] && continue

  # Description
  desc=""
  if [ -f "$d/README.md" ]; then
    desc=$(awk 'NR>1 && /^>/ {sub(/^> */, ""); print; exit}' "$d/README.md")
    [ -z "$desc" ] && desc=$(awk 'NR>1 && /^[^#\[]/ && NF>0 {print; exit}' "$d/README.md" | head -c 200)
  fi
  [ -z "$desc" ] && desc="(설명 없음)"
  DESCS["$slug"]="$desc"

  # Stack
  tech=""
  [ -f "$d/tsconfig.json" ] && tech="TypeScript"
  [ -z "$tech" ] && [ -f "$d/package.json" ] && tech="Node.js"
  [ -f "$d/pyproject.toml" ] && tech="${tech:+$tech/}Python"
  [ -z "$tech" ] && tech="Other"
  STACKS["$slug"]="$tech"

  # Category (keyword-based)
  lower_desc=$(echo "$desc $slug" | tr '[:upper:]' '[:lower:]')
  cat="Other"
  # Category matching (order matters - more specific patterns first)
  if echo "$lower_desc" | grep -qE "llm.*(context|qual|serve|monitor)|embedding.migr|long.context|토큰.*분석|vram.*(추정|모니터)|resource.monitor"; then
    cat="LLM Ops & Debugging"
  elif echo "$lower_desc" | grep -qE "vibe.code|tree.sitter|code.*(change|perf|audit)|secret.scrub|ai-code.*(change|perf)|sql.*guard|static.guard"; then
    cat="AI Code Quality & DevTools"
  elif echo "$lower_desc" | grep -qE "agent|에이전트|agentic|llm.*(mesh|route|stabil)|runtime.debug|mcp.*런타임"; then
    cat="AI Agent & LLM Infra"
  elif echo "$lower_desc" | grep -qE "ci-yaml|deploy|log.incident|webhook|chaos"; then
    cat="CI/CD & Infrastructure"
  elif echo "$lower_desc" | grep -qE "seo|web.health|search.guard|크롤러|팬텀"; then
    cat="Web & SEO"
  elif echo "$lower_desc" | grep -qE "doc.*(structure|fresh)|slide|rag.doc|pdf|markdown|launch.kit"; then
    cat="Document & Content"
  elif echo "$lower_desc" | grep -qE "indie|small.biz|queue|email.cleanup|community.*keyword|community.*monitor"; then
    cat="Indie / Small Biz"
  elif echo "$lower_desc" | grep -qE "iot|local.first|openapi|data.guard"; then
    cat="IoT & Data"
  fi
  CATEGORIES["$slug"]="$cat"
done

TOTAL=${#DESCS[@]}

# --- Category order ---
CAT_ORDER=(
  "AI Agent & LLM Infra"
  "AI Code Quality & DevTools"
  "LLM Ops & Debugging"
  "CI/CD & Infrastructure"
  "Web & SEO"
  "Document & Content"
  "Indie / Small Biz"
  "IoT & Data"
  "Other"
)

# --- Generate README ---
cat > README.md <<'HEADER'
# Prototypes

커뮤니티(HN, Reddit, GeekNews, GitHub Trending)에서 발굴한 개발자 pain point를 자동으로 프로토타이핑하는 파이프라인의 산출물.

> crawl → analyze → ideate → select → spawn

각 프로토타입은 독립 실행 가능한 단위로, 자동 생성 후 이 레포에 커밋됩니다.

## Architecture

```
Community Sources                 Pipeline (cron-automated)                    Output
─────────────────    ──────────────────────────────────────────    ──────────────────

  HN ─────────┐     ┌──────────┐    ┌──────────┐                 pain-points/
  Reddit ─────┼────▶│  Crawl   │───▶│ Analyze  │────────────────▶  2026-03-16-hn.jsonl
  GeekNews ───┤     │  (bash)  │    │ (claude) │                   2026-03-16-reddit.jsonl
  GH Trend ───┘     │  */10min │    │  /3hour  │                   ...
                     └──────────┘    └────┬─────┘
                                          │
                                          ▼
                                    ┌──────────┐                  ideas/
                                    │  Ideate  │─────────────────▶  ai-code-change-tracker.md
                                    │ (claude) │                    local-agent-mesh.md
                                    │  /3hour  │                    ...
                                    └────┬─────┘
                                         │
                                         ▼
                                    ┌──────────┐                  specs/
                                    │  Select  │─────────────────▶  ai-code-change-tracker.md
                                    │ (claude) │  approve/reject    small-biz-queue-ops.md
                                    │  /6hour  │                    ...
                                    └────┬─────┘
                                         │
                                         ▼
                                    ┌──────────┐                  prototypes/  ← this repo
                                    │  Spawn   │─────────────────▶  ai-code-change-tracker/
                                    │ (claude) │  git commit+push   small-biz-queue-ops/
                                    │  /6hour  │                    ...
                                    └──────────┘
```

## Demo: Pipeline in Action

**1. Crawl** — 커뮤니티 게시물을 10분마다 수집

```json
{"id":"1rupekm","source":"reddit","pain_point":"AI 코딩 도구로 생성된 코드의 downstream 영향 추적이 불가능","signal_strength":4,"tags":["ai-coding","devtools"]}
```

**2. Analyze** — Claude가 pain point를 추출·분류 (signal_strength 1-5)

```
483개 게시물 → 88개 pain points 추출 (중복 제거 후)
├── Reddit:  30 (sig3: 26, sig2: 4)
├── HN:      36 (sig3: 29, sig2: 7)
├── GeekNews: 5 (sig3: 4, sig2: 1)
└── GitHub:  17 (sig4: 5, sig3: 11, sig2: 1)
```

**3. Ideate** — pain point 클러스터링 → 아이디어 생성

```markdown
# AI 코드 변경 영향 추적기
> tree-sitter AST + git diff로 코드 변경의 downstream 영향 범위를 추적

## Pain Points 근거
| 출처 | Signal | Pain Point |
|------|--------|------------|
| reddit | 5 | 바이브코딩으로 만든 앱의 품질·보안이 심각하게 우려 |
| hn     | 4 | AI 코딩 도구 과사용 시 인지적 부채 발생 |
| geeknews | 4 | AI 시대에 테스트 코드 없으면 안정성 유지 불가 |
```

**4. Select** — 3인 가상 심의위원이 승인/기각 결정

```json
{"slug":"ai-code-change-tracker","status":"approved","scores":{"authenticity":4.3,"prototypability":4.0,"freshness":3.7,"learning":4.7}}
```

**5. Spawn** — Claude가 spec 기반으로 프로토타입 자동 구현

```
# STATUS: SUCCESS
- [x] git diff 파싱 → tree-sitter로 변경된 함수/클래스 식별
- [x] 변경된 심볼의 1-hop downstream 영향 트리 시각화 (CLI)
- [x] spec 문서와 실제 코드 구현체 매핑
- [x] "구현됨 / 미구현 / 코드에만 존재" 상태 출력
```

---

HEADER

# --- Write category tables ---
for cat in "${CAT_ORDER[@]}"; do
  # Collect slugs for this category
  slugs=()
  for slug in $(echo "${!CATEGORIES[@]}" | tr ' ' '\n' | sort); do
    [ "${CATEGORIES[$slug]}" = "$cat" ] && slugs+=("$slug")
  done
  [ ${#slugs[@]} -eq 0 ] && continue

  cat >> README.md <<EOF
### $cat

| Prototype | Description | Stack |
|-----------|-------------|-------|
EOF

  for slug in "${slugs[@]}"; do
    desc="${DESCS[$slug]}"
    stack="${STACKS[$slug]}"
    echo "| [$slug](./$slug) | $desc | $stack |" >> README.md
  done

  echo "" >> README.md
done

# --- Footer ---
cat >> README.md <<EOF
---

**Total: ${TOTAL} prototypes** | Auto-updated by prototype-pipeline
EOF

echo "README.md updated (${TOTAL} prototypes)"
