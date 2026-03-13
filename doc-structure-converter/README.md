# doc-structure-converter

> Structure-aware Markdown to PDF converter that prevents tables and code blocks from splitting across page boundaries.

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
