# OSS Search Guard

> Detect impersonation sites in search results for open-source projects.

## Architecture

```
┌─────────────────────┐
│   CLI (cli.py)      │
│   사용자 입력 처리     │
└────────┬────────────┘
         │ GitHub repo URL
         ▼
┌─────────────────────┐     ┌──────────────────────┐
│  GitHub Parser      │────▶│  GitHub API          │
│  (github_parser.py) │◀────│  (public REST API)   │
│                     │     └──────────────────────┘
│  · URL 파싱          │
│  · 공식 도메인 추출    │
│  · homepage 수집     │
└────────┬────────────┘
         │ project_info + official_domains
         ▼
┌─────────────────────┐     ┌──────────────────────┐
│  Searcher           │────▶│  DuckDuckGo          │
│  (searcher.py)      │◀────│  (검색 엔진)          │
│                     │     └──────────────────────┘
│  · 3종 쿼리 검색      │
│    "{name}"          │
│    "{name} download" │
│    "{name} official" │
│  · 중복 제거          │
│  · 관련성 필터링       │
└────────┬────────────┘
         │ filtered results[]
         ▼
┌─────────────────────┐
│  Analyzer           │
│  (analyzer.py)      │
│                     │
│  · 공식/신뢰 도메인    │
│  · 도메인명 일치 검사   │
│  · typosquatting     │
│    유사도 (difflib)   │
│  · 의심 TLD 검사      │
│  · 의심 키워드 검사    │
│  · risk_score 산출   │
└────────┬────────────┘
         │ analyses[] (scored & sorted)
         ▼
┌─────────────────────┐
│  Reporter           │
│  (reporter.py)      │
│                     │
│  · ANSI 컬러 리포트   │
│  · DANGER / WARNING  │
│    / SAFE 분류       │
│  · 위협 요약 출력      │
└─────────────────────┘
```

## Demo

```bash
$ uv run oss-search-guard https://github.com/lh3/minimap2

[1/3] Parsing GitHub repository...
  Project: minimap2
  Owner:   lh3
  Homepage: https://lh3.github.io/minimap2/
  Official domains: github.com, lh3.github.io, ...

[2/3] Searching DuckDuckGo...
  Collected 42 unique results
  Relevant results: 18

[3/3] Analyzing search results...

======================================================================
  OSS Search Guard — Threat Report
======================================================================

  Project:  minimap2
  GitHub:   https://github.com/lh3/minimap2

  Overall Threat Level: DANGER
  Found 1 dangerous result(s) in search results!

  Summary: 14 safe / 3 warning / 1 danger (out of 18 results)

  --- DANGEROUS RESULTS ---

    [DANGER] minimap2.download (score: 70)
      URL:   https://minimap2.download/latest
      Title: Minimap2 — Free Download
      > Domain exactly matches project name 'minimap2' — likely impersonation
      > Suspicious TLD: .download

  --- SUSPICIOUS RESULTS ---

    [WARNING] minimap2-tool.xyz (score: 35)
      URL:   https://minimap2-tool.xyz/
      > Domain contains project name 'minimap2'
      > Suspicious TLD: .xyz

  --- SAFE RESULTS ---

    [OFFICIAL] github.com
    [OFFICIAL] lh3.github.io
    [OK]       stackoverflow.com
    ...

======================================================================
```

## 실행 방법

```bash
# 의존성 설치
uv sync

# 실행
uv run oss-search-guard <github-repo-url>

# 예시
uv run oss-search-guard https://github.com/lh3/minimap2
uv run oss-search-guard https://github.com/qarmin/czkawka
uv run oss-search-guard https://github.com/nicotine-plus/nicotine-plus
```

## 동작 방식

1. GitHub 레포 URL에서 프로젝트명과 공식 URL을 자동 추출 (GitHub API 활용)
2. DuckDuckGo에서 프로젝트명으로 3가지 쿼리 검색 (이름, "download", "official site")
3. 검색 결과를 휴리스틱으로 분석:
   - 도메인이 프로젝트명과 정확히 일치하는지 (impersonation)
   - 도메인 유사도 (typosquatting)
   - 의심스러운 TLD (.xyz, .download 등)
   - 의심 키워드 (crack, keygen, free download 등)
4. 위협 수준 리포트 출력 (DANGER / WARNING / SAFE)

## 구조

```
oss-search-guard/
├── oss_search_guard/
│   ├── __init__.py
│   ├── cli.py            # CLI 진입점
│   ├── github_parser.py  # GitHub URL 파싱 + 공식 URL 추출
│   ├── searcher.py       # DuckDuckGo 검색 + 관련성 필터링
│   ├── analyzer.py       # 도메인 위험도 분석 휴리스틱
│   └── reporter.py       # ANSI 색상 CLI 리포트
├── pyproject.toml
├── BUILD_LOG.md
├── STATUS.md
└── README.md
```

## 원본
prototype-pipeline spec: oss-search-guard
