# 개인 웹 아카이브 검색 엔진

> URL을 입력하면 본문을 추출하여 로컬 SQLite FTS5로 한국어+영어 전문 검색을 제공하는 프로토타입

## Architecture

```
URL 입력 (CLI/Web UI)
    │
    ▼
┌──────────────┐     ┌──────────────┐
│  node-fetch  │────▶│ @mozilla/    │
│  (HTTP GET)  │     │ readability  │
└──────────────┘     └──────┬───────┘
                            │ title, content, excerpt
                            ▼
                   ┌──────────────────┐
                   │  SQLite FTS5     │
                   │  (trigram 토크나이저) │
                   │                  │
                   │  pages ◀─sync─▶  │
                   │  pages_fts       │
                   └────────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         CLI 검색      Web UI 검색    REST API
       (cli.js)     (index.html)   (/api/*)
```

## Demo

### CLI — URL 추가 및 검색

```
$ node cli.js add "https://ko.wikipedia.org/wiki/대한민국"
Fetching: https://ko.wikipedia.org/wiki/대한민국
✓ Added: "대한민국" (ko, 66835 chars)

$ node cli.js search "한국어"
Found 1 result(s):

  대한민국
  https://ko.wikipedia.org/wiki/대한민국
  …공용어는 한국어이며 수도는 서울특별시이다…

$ node cli.js search "javascript"
Found 1 result(s):

  Node.js
  https://en.wikipedia.org/wiki/Node.js
  …Node.js runs on the V8 JavaScript engine…
```

### Web UI

웹 서버 (`node server.js`) 실행 후 `http://localhost:3777`에서:
- 검색창에 한국어/영어 입력 → 결과 목록 + 하이라이트 스니펫
- URL 입력란에 주소 붙여넣기 → 아카이브에 추가

## 토크나이저 비교 결과

`node tokenizer-comparison.js` 실행 결과:

| Query | trigram | unicode61 |
|-------|---------|-----------|
| 인공지능 (3글자+) | PASS | PASS |
| 서울 (2글자) | PASS | PASS |
| 김치 (2글자) | PASS | FAIL |
| JavaScript | PASS | PASS |
| machine learning | PASS | FAIL |
| React (혼합문서) | PASS | FAIL |
| 프론트엔드 (혼합문서) | PASS | PASS |
| 떡볶이 (3글자) | PASS | PASS |
| **Score** | **8/8** | **5/8** |

**trigram 선택 이유**: CJK 바이트 레벨 trigram이 한국어를 공백 없이도 서브스트링 매칭 가능. 2글자 미만 쿼리는 LIKE 폴백 처리. mecab-ko는 형태소 분석 품질이 최고이나 시스템 패키지 의존성이 필요하여 프로토타입에는 부적합.

## 실행 방법

```bash
# 의존성 설치
npm install

# CLI 사용
node cli.js add <url>       # URL 아카이브에 추가
node cli.js search <query>  # 검색
node cli.js list            # 목록 조회

# 웹 서버
node server.js              # http://localhost:3777

# 토크나이저 비교
node tokenizer-comparison.js
```

## 구조

```
personal-web-archive-search/
├── cli.js                    # CLI 인터페이스
├── server.js                 # HTTP 서버 (API + 정적 파일)
├── index.html                # 검색 웹 UI
├── db.js                     # SQLite FTS5 데이터베이스 레이어
├── extractor.js              # URL → readability 본문 추출
├── tokenizer-comparison.js   # 토크나이저 성능 비교 스크립트
├── BUILD_LOG.md              # 빌드 일지
├── STATUS.md                 # 결과 상태
└── README.md                 # 이 파일
```

## 원본
prototype-pipeline spec: personal-web-archive-search
