# OSS Search Guard

> Detect impersonation sites in search results for open-source projects.

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
