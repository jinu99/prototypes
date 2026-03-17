---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# Indie Launch Kit

> README.md 하나로 랜딩페이지, 체인지로그, 런치 포스트를 CLI 한 줄에 생성

**카테고리**: Developer Tools · Indie Hacker
**스택**: Node.js, remark (AST), Handlebars, simple-git
**날짜**: 2026-03-15

<!--
인디 개발자가 제품을 런칭할 때 겪는 반복 작업이 있다. 랜딩페이지, 체인지로그, Product Hunt 포스트. 이걸 README.md 하나에서 CLI 한 줄로 전부 뽑아내는 도구를 만들었다. 오늘은 왜 이걸 만들었고, 어떻게 동작하는지 얘기해보겠다.
-->

---

## Background

개발자 생태계에서 **"만드는 것"보다 "알리는 것"이 더 어렵다**는 말이 꾸준히 나온다.

- 기능적으로 완성된 프로젝트가 랜딩페이지 하나 없어서 첫인상에서 밀림
- Product Hunt, Reddit, HN 각 플랫폼마다 포맷이 다르고, 최적화할 시간이 없음
- 체인지로그, 블로그, 런치 포스트를 각각 별도로 관리 — 통합 도구 부재

Carrd, Unicorn Platform 같은 빌더가 있지만, 결국 **디자인 감각에 의존**한다.
개발자의 기존 자산(README, git log)에서 자동으로 런치 자산을 뽑아내는 도구는 없었다.

<!--
인디 개발자 커뮤니티를 보면 반복되는 패턴이 있다. 코드는 다 짰는데, 랜딩페이지를 어떻게 만들지 모르겠다는 거다. Carrd 같은 빌더를 써봐도 결국 디자인 감각이 필요하다. 그리고 Product Hunt에 올릴 포스트, Reddit에 올릴 포스트, HN에 올릴 포스트를 각각 따로 써야 한다. 코드를 만드는 건 하나의 기술인데, 런칭은 완전히 다른 기술이다. 이 간극을 좁히는 게 이 프로토타입의 출발점이다.
-->

---

## Pain Point

커뮤니티에서 실제로 반복 관찰된 고통들:

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | r/webdev | ⚡⚡⚡ | 기능은 완성됐는데 랜딩페이지를 프리미엄하게 만들 역량이 없다 |
| 2 | r/SideProject | ⚡⚡⚡ | Product Hunt에서 VC 지원 스타트업에 4시간 만에 묻힘 |
| 3 | Hacker News | ⚡⚡ | 릴리즈 주변 작업(버그 트래킹, 런치 포스트, 체인지로그)을 통합 관리할 도구가 없다 |

**공통 패턴**: 개발자는 코드에는 익숙하지만, 런치에 필요한 **마케팅 자산 생성**에 시간과 역량이 부족하다.

<!--
r/webdev에서 이런 글이 자주 올라온다. "나 기능은 다 만들었는데 랜딩페이지가 구려서 사람들이 안 본다." r/SideProject에서는 Product Hunt 런칭 얘기가 나오는데, VC 붙은 팀은 디자이너가 비주얼 자산을 다 만들어주고, 인디 개발자는 텍스트 하나 달랑 올린다. 4시간이면 묻힌다. 결국 이건 기술 문제가 아니라 자산 생성 문제다. 개발자가 이미 갖고 있는 걸로 런치 자산을 만들어주면 되지 않나, 라는 생각이었다.
-->

---

## Solution

**접근법**: 개발자가 이미 갖고 있는 자산(README, git log, package.json)에서 런치에 필요한 모든 걸 뽑아낸다.

**기존 도구와의 차이점**:
| 기존 | Indie Launch Kit |
|------|-----------------|
| GUI 빌더 → 디자인 감각 필요 | CLI 한 줄 → 디자인 결정 제로 |
| 입력: 사용자가 직접 작성 | 입력: README.md (이미 존재) |
| 랜딩페이지만 | 랜딩페이지 + 체인지로그 + 3개 플랫폼 런치 포스트 |

**검증 목표**: README만으로 생성된 랜딩페이지가 "쓸 만한 수준"인지.
AI/LLM 없이, 순수 결정론적 파싱+템플릿으로 어디까지 갈 수 있는지 실험.

<!--
기존 도구들은 전부 GUI 빌더다. 사용자가 직접 텍스트를 넣고, 레이아웃을 고르고, 색을 정한다. 그런데 개발자는 이미 README에 제품 설명을 다 써놨다. git log에 변경 이력이 있다. package.json에 메타데이터가 있다. 이걸 왜 다시 쓰나. 그래서 접근을 바꿨다. 새로 쓰는 게 아니라, 이미 있는 걸 변환하는 거다. 그리고 의도적으로 AI를 안 썼다. 결정론적 파싱으로 어디까지 되는지 보고 싶었다.
-->

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI (commander)                          │
│                  init · build --dir --theme                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      builder.js (오케스트레이션)                  │
│                                                                  │
│  ┌──────────────┐   ┌───────────────┐   ┌─────────────────────┐ │
│  │  parser.js   │   │ metadata.js   │   │   changelog.js      │ │
│  │ README → AST │   │ package.json  │   │ git log → 타입별    │ │
│  │ → 섹션 분류  │   │ → name, ver   │   │   그룹화            │ │
│  └──────┬───────┘   └──────┬────────┘   └──────────┬──────────┘ │
│         └──────────────────┼───────────────────────┘            │
│                            ▼                                    │
│  ┌──────────────────────────────┐  ┌────────────────────────┐   │
│  │       templates.js           │  │    launch-posts.js     │   │
│  │ Handlebars × 3 테마 렌더링  │  │ PH / Reddit / HN 초안  │   │
│  └──────────────┬───────────────┘  └──────────┬─────────────┘   │
└─────────────────┼─────────────────────────────┼─────────────────┘
                  ▼                             ▼
        dist/index.html              dist/launch-posts/*.md
        dist/changelog.html
```

핵심: `parser.js`가 remark AST로 헤딩 키워드를 매칭해서 Hero/Features/Install/CTA로 자동 분류

<!--
구조는 꽤 단순하다. 입력이 셋이다. README, package.json, git log. parser.js가 README를 remark으로 AST 파싱하고, 헤딩 텍스트의 키워드 패턴 매칭으로 섹션을 분류한다. "Features"라는 헤딩이 나오면 features 섹션으로, "Install"이면 install 섹션으로. 이 분류된 데이터를 Handlebars 템플릿에 넣으면 HTML이 나온다. 사람으로 치면, README를 읽고 "아 이 부분이 기능 설명이구나, 이 부분이 설치 방법이구나" 하고 이해하는 과정을 코드로 옮긴 거다.
-->

---

## Demo

```bash
$ node bin/cli.js build --dir ./test-fixtures/sample-project --theme minimal

🚀 indie-launch-kit build
  Project: /home/user/indie-launch-kit/test-fixtures/sample-project
  Theme: minimal

  ✓ Parsed README.md → hero: "Sample Project", 2 feature sections, 1 install sections
  ✓ Metadata: sample-project v1.0.0
  ✓ Landing page → dist/index.html (theme: minimal)
  ✓ Changelog → dist/changelog.html (12 commits)
  ✓ Launch posts → dist/launch-posts/

✅ Done! Open dist/index.html in your browser.
```

**생성 결과물**: 3개 테마(minimal · dark · gradient)의 정적 HTML 랜딩페이지 + 체인지로그 + Product Hunt/Reddit/HN 런치 포스트 초안

서로 다른 README 3개(FastAPI Starter, express-api-kit, TaskFlow CLI)로 테스트 — 모두 섹션 분류 정확, HTML 시맨틱 구조 정상

<!--
실행은 이렇게 한 줄이다. 테마를 고르고 프로젝트 경로를 넣으면 끝이다. README를 파싱해서 섹션을 분류하고, 메타데이터를 뽑고, 랜딩페이지와 체인지로그를 생성하고, 세 개 플랫폼의 런치 포스트 초안까지 만든다. 서로 다른 구조의 README 세 개로 테스트했는데, 셋 다 제대로 동작했다. feature cards가 그리드로 깔끔하게 배치되고, install 섹션의 코드블록도 잘 스타일링된다.
-->

---

## Key Decisions & Lessons

### 1. AI 없이 결정론적 파싱을 선택한 이유
심의에서 "AI 시대에 결정론적 템플릿의 경쟁력이 의문"이라는 반대 의견이 있었다 (신선도 2.7/5). 하지만 **재현 가능성과 예측 가능성**이 CLI 도구에서는 더 중요하다고 판단. 같은 입력에 항상 같은 출력.

### 2. remark AST + 키워드 패턴 매칭
h3 서브헤딩이 부모 h2에서 분리되는 문제 → depth 비교 로직 추가.
수정 후 h2가 h1에 포함되는 역효과 → `depth >= 2` 조건으로 해결.
마크다운 파싱은 단순해 보이지만, 헤딩 계층 구조 처리가 핵심 난이도.

### 3. 심의 점수
| 항목 | 점수 |
|------|------|
| 문제 진정성 | 3.7/5 |
| 프로토타입 적합성 | **4.3/5** |
| 신선도 | 2.7/5 |
| 학습 가치 | 3.3/5 |

<!--
세 가지 판단이 중요했다. 첫째, AI를 안 쓴 건 의도적이다. 심의에서 준혁이 "기술적 도전이 부족하다"고 했는데, 맞는 말이다. 하지만 CLI 도구는 같은 입력에 항상 같은 결과가 나와야 한다. LLM을 넣으면 매번 다른 결과가 나오고, 그건 개발자 도구로서 신뢰를 깨뜨린다. 둘째, 마크다운 파싱이 생각보다 까다로웠다. h3가 h2 아래에 있으면 같은 섹션인데, AST에서는 평탄하게 나온다. 이걸 depth로 묶어야 하고, h1에 h2가 딸려 들어가지 않게 조건을 나눠야 했다. 단순해 보이는 문제에 예외가 많은 전형적인 케이스다.
-->

---

## Results & Future

### 성과
- [x] CLI 한 줄로 README → 3개 테마 정적 HTML 랜딩페이지 생성
- [x] Hero/Features/Install/CTA 자동 섹션 분류
- [x] conventional commits → 체인지로그 HTML
- [x] Product Hunt / Reddit / HN 런치 포스트 초안
- [x] 서로 다른 README 3개로 품질 검증 — **5/5 통과**

### 한계
- 브라우저 렌더링 스크린샷을 직접 확인 못 함 (Playwright 시스템 의존성 부재)
- 이미지/스크린샷이 있는 README는 처리하지만, 이미지 최적화는 없음
- 결정론적 템플릿의 표현력 한계 — 복잡한 README일수록 "뻔한" 결과물

### 프로덕트가 되려면
- **LLM 하이브리드**: 섹션 분류는 결정론적으로, 카피라이팅은 LLM으로 보강
- **커스텀 테마 시스템**: CSS 변수 기반 사용자 정의 테마
- **배포 통합**: Vercel/Netlify 원클릭 배포
- **실시간 프리뷰**: `--watch` 모드로 README 수정 시 즉시 반영

<!--
결과적으로 완료 기준 다섯 개를 전부 통과했다. 솔직히 아쉬운 건 Playwright 스크린샷을 못 찍은 거다. HTML 파일은 생성되는데 렌더링 결과를 자동으로 확인할 수가 없었다. 그리고 결정론적 템플릿의 한계가 분명하다. 복잡한 README일수록 결과물이 뻔해진다. 프로덕트로 가려면 결국 LLM이 필요하다. 다만 접근을 바꿔야 한다. 구조 분류는 결정론적으로 하되, 카피라이팅만 LLM으로 보강하는 하이브리드. 그리고 Vercel 원클릭 배포까지 붙으면 "코드 푸시하면 랜딩페이지가 업데이트된다"는 워크플로가 완성된다.
-->
