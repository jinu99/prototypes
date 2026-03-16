# doc-structure-converter

> Structure-aware Markdown to PDF converter that prevents tables and code blocks from splitting across page boundaries.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.js)                            │
│              convert  │  analyze  │  compare                    │
└────────┬──────────────┴─────┬─────┴──────┬──────────────────────┘
         │                    │            │
         ▼                    ▼            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Parser (parser.js)                         │
│                                                                 │
│  Markdown ──▶ remark + GFM ──▶ AST ──▶ Block 식별              │
│                                        ┌──────────────────┐    │
│                                        │ breakable 판정   │    │
│                                        │ table  → false   │    │
│                                        │ code   → false   │    │
│                                        │ image  → false   │    │
│                                        │ 나머지 → true    │    │
│                                        └──────────────────┘    │
└────────┬────────────────────┬────────────────────┬──────────────┘
         │                    │                    │
    convert/compare       analyze             compare
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐
│ Typst Generator  │  │ 구조 통계    │  │  Compare (compare.js)│
│ (typst-gen.js)   │  │ 출력 (CLI)   │  │                      │
│                  │  └──────────────┘  │  Pandoc PDF (before)  │
│ AST blocks       │                    │        vs             │
│   ──▶ Typst 마크업│                    │  docconv PDF (after)  │
│   + breakable    │                    └──────────┬───────────┘
│     hints        │                               │
└────────┬─────────┘                               │
         │                                         │
         ▼                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Renderer (renderer.js)                        │
│                                                                 │
│  ┌─────────────────────┐      ┌──────────────────────┐         │
│  │ Typst CLI compile   │      │ Pandoc + Typst engine │         │
│  │ (structure-aware)   │      │ (baseline 비교용)     │         │
│  └──────────┬──────────┘      └──────────┬───────────┘         │
│             ▼                            ▼                      │
│         docconv.pdf                  pandoc.pdf                  │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 아이디어**: table, code block, image를 `#block(breakable: false)`로 감싸서 페이지 경계에서 분리되지 않도록 Typst에 힌트를 전달한다.

## Demo

### 1. 문서 구조 분석 (`analyze`)

```bash
$ node src/cli.js analyze test-data/sample.md

Document Analysis: /path/to/test-data/sample.md

Total blocks: 22
  Headings:    5
  Tables:      4
  Code blocks: 5
  Lists:       3
  Images:      0
  Unbreakable: 9

Block sequence:
  1.    heading
  2.    paragraph
  3. 🔒 table
  4.    paragraph
  5. 🔒 code
  ...
```

### 2. Markdown → PDF 변환 (`convert`)

```bash
# 기본 변환
$ node src/cli.js convert test-data/sample.md -o output/result.pdf
Converting: /path/to/test-data/sample.md
  Parsed 22 blocks (9 unbreakable)
  ✓ PDF saved: /path/to/output/result.pdf

# 중간 Typst 파일 확인 (디버그 모드)
$ node src/cli.js convert test-data/sample.md -o output/result.pdf --debug
  Debug Typst saved: output/result.typ
  ✓ PDF saved: output/result.pdf
```

### 3. Pandoc과 Before/After 비교 (`compare`)

```bash
$ node src/cli.js compare test-data/sample.md -d output

=== Before/After Comparison: sample ===

Document stats:
  Blocks: 22
  Tables: 4
  Code blocks: 5
  Lists: 3
  Unbreakable blocks: 9

[BEFORE] Pandoc default → output/sample-pandoc.pdf
  ✓ Pandoc PDF generated

[AFTER] docconv (structure-aware) → output/sample-docconv.pdf
  ✓ docconv PDF generated

=== Compare the two PDFs ===
  Pandoc (baseline): output/sample-pandoc.pdf
  docconv (ours):    output/sample-docconv.pdf
  Look for: tables/code blocks split across pages in Pandoc but not in docconv
```

Pandoc 기본 출력에서는 table과 code block이 페이지 경계에서 잘리지만, docconv 출력에서는 블록 단위로 페이지를 넘겨 깔끔하게 유지된다.

## 실행 방법

```bash
# 사전 요구: Typst CLI, Pandoc (비교용)
# https://github.com/typst/typst/releases
# https://github.com/jgm/pandoc/releases

# 의존성 설치
npm install

# Markdown → PDF 변환
node src/cli.js convert test-data/sample.md -o output/result.pdf

# 문서 구조 분석
node src/cli.js analyze test-data/sample.md

# Pandoc과 before/after 비교
node src/cli.js compare test-data/sample.md -d output
```

## 구조

```
src/
  cli.js          CLI 진입점 (convert, compare, analyze)
  parser.js       Markdown→AST 파싱 + 블록 경계 식별
  typst-gen.js    AST→Typst 마크업 변환 (breakable 힌트)
  renderer.js     Typst CLI / Pandoc PDF 렌더링
  compare.js      Before/after 비교 로직
test-data/
  sample.md       테스트용 Markdown (표 4개, 코드블록 5개)
output/           생성된 PDF 파일
```

## 원본
prototype-pipeline spec: doc-structure-converter
