---
marp: true
theme: default
paginate: true
backgroundColor: #fafafa
---

# CI/CD YAML 자동 생성기

**프로젝트 디렉토리를 스캔하면 GitHub Actions CI 워크플로우가 나온다**

- Category: Developer Tooling / CI-CD
- Stack: Node.js, js-yaml, @iarna/toml
- Date: 2026-03-10

<!--
이번에 만든 프로토타입은 CI/CD YAML 자동 생성기다.
프로젝트 디렉토리를 한번 스캔하면 GitHub Actions 워크플로우 YAML이 바로 나오는 CLI 도구인데,
왜 이걸 만들었는지부터 얘기해보겠다.
-->

---

## Background

**CI/CD 파이프라인 YAML, 매번 처음부터 쓰고 있다**

- 새 프로젝트를 시작할 때마다 반복되는 패턴: 이전 프로젝트에서 YAML을 복사하고, 절반을 수정하고, 나머지 절반을 깨뜨린다
- GitHub Actions가 표준이 되면서 YAML 파이프라인의 복잡도가 계속 올라가고 있다 — lint, test, build에 보안 게이트(SAST, secret scan)까지
- 들여쓰기 한 칸 틀려서 디버깅에 30분 쓰는 일이 반복된다
- 결국 **"설정 파일을 작성하는 데 드는 시간"이 실제 코드 작성 시간을 잡아먹는** 문제

<!--
개발자들이 새 프로젝트를 시작할 때 하는 일 중 하나가 CI/CD 파이프라인을 세팅하는 건데,
이게 생각보다 꽤 귀찮은 작업이다.
보통 이전 프로젝트에서 YAML을 복사해오는데, 복사해서 절반을 고치면 나머지 절반이 깨진다.
GitHub Actions가 사실상 표준이 되면서 파이프라인에 들어가야 할 게 점점 많아지고 있고,
결국 설정 파일 만드는 데 드는 시간이 코드 쓰는 시간을 잡아먹는 상황이 반복된다.
-->

---

## Pain Point

**커뮤니티에서 실제로 나오는 불만들**

| # | 출처 | Signal | Pain Point |
|---|------|:------:|------------|
| 1 | Hacker News | ★★★ | 새 SaaS 프로젝트마다 CI/CD 파이프라인(SAST, DAST, E2E, SBOM)을 YAML로 처음부터 구성해야 한다 |
| 2 | r/SideProject | ★★★ | GitHub Actions YAML을 프로젝트마다 복사-붙여넣기하고 들여쓰기 디버깅에 수시간을 소비한다 |
| 3 | r/programming | ★★★ | SQL 변경사항이 정적 분석 없이 프로덕션에 도달한다 — 보안 게이트 누락 |

- 3개 출처 모두 **Signal Strength 3** — 단순 불편이 아니라 반복적 시간 낭비
- 공통 패턴: 수동 작성 → 실수 → 디버깅 → 또 수동 작성

<!--
HN이랑 Reddit에서 이 주제로 꽤 강한 시그널이 나온다.
단순히 불편하다는 게 아니라, 실제로 시간을 수시간 단위로 잡아먹는다는 보고가 반복된다.
세 출처 모두 signal strength가 3이었는데, 공통 패턴이 있다.
수동으로 쓰고, 실수하고, 디버깅하고, 다음 프로젝트에서 또 수동으로 쓰는 루프다.
결국 이건 자동화가 안 되고 있는 반복 작업 문제다.
-->

---

## Solution

**`ci-gen init .` — 프로젝트를 읽고, 파이프라인을 생성한다**

- 핵심 아이디어: 프로젝트 설정 파일(`package.json`, `pyproject.toml`, `go.mod`)을 파싱해서 언어, 패키지 매니저, 테스트 러너, 린터를 **자동 감지**
- 감지 결과를 기반으로 **lint → test → build → security** 파이프라인을 완성된 YAML로 출력
- 기존 솔루션과의 차이점:

| 기존 도구 | 한계 | 우리 접근 |
|-----------|------|-----------|
| GitHub 스타터 워크플로우 | 수동 선택 필요, 프로젝트 분석 없음 | 자동 감지 |
| Ghygen | PHP/Laravel 전용 | 3개 에코시스템 범용 |
| github-workflows-kt | Kotlin DSL, 자동 감지 없음 | 파일 스캔 기반 자동 |
| AI 기반 도구 | API 키 필수, 비용 발생 | 로컬 실행, 무료 |

<!--
그래서 만든 게 ci-gen init이라는 CLI 도구다.
프로젝트 디렉토리를 지정하면 설정 파일을 파싱해서 어떤 언어를 쓰고 있는지, 테스트 러너가 뭔지, 린터가 뭔지를 자동으로 감지한다.
기존 도구들이 있긴 한데, 대부분 특정 언어 전용이거나 수동 선택이 필요하거나 API 키가 필요하다.
언어 무관하게 프로젝트를 분석해서 보안 게이트까지 포함한 완전한 YAML을 생성하는 무료 범용 CLI는 없었다.
-->

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.js)                            │
│              init / detect / validate 명령 라우팅                │
└──────┬──────────────────┬───────────────────┬───────────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌──────────────┐  ┌───────────────┐  ┌────────────────┐
│   Detector   │  │   Generator   │  │   Validator    │
│ detector.js  │  │ generator.js  │  │  validator.js  │
├──────────────┤  ├───────────────┤  ├────────────────┤
│ 프로젝트 파일│  │ Detection →   │  │ YAML 파싱     │
│ 스캔 + 에코  │  │ Job 구성으로  │  │ + GitHub      │
│ 시스템 감지  │  │ 변환          │  │ Actions 스키마 │
└──────────────┘  └───────────────┘  │ 검증           │
       ▲                              └────────────────┘
       │
┌──────────────┐
│  rules.json  │  ← 감지 규칙 설정 (3개 에코시스템 × 도구 매핑)
└──────────────┘
```

- **Detector**: 파일 존재 확인 + 설정 파일 파싱으로 도구 체인 식별
- **Generator**: 감지 결과를 GitHub Actions job 구조로 변환, matrix strategy 자동 적용
- **Validator**: 생성된 YAML의 문법 + 구조적 유효성 검증
- **rules.json**: 감지 규칙이 코드 밖에 있어서 새 에코시스템 추가 시 JSON만 수정

<!--
구조는 꽤 단순하다. CLI가 명령을 라우팅하고, 세 개의 모듈이 각자 역할을 한다.
Detector가 프로젝트를 스캔하고, Generator가 YAML을 만들고, Validator가 검증한다.
한 가지 의식적으로 한 판단이 있는데, 감지 규칙을 rules.json으로 코드 밖에 분리한 거다.
새 에코시스템을 추가하고 싶으면 JSON에 규칙만 추가하면 되니까 확장이 쉽다.
-->

---

## Demo

### Node.js 프로젝트 → 완성된 CI 파이프라인

```bash
$ node src/cli.js init samples/node-project --dry-run

🔍 Scanning project: samples/node-project

✅ Detected: Node.js
   Package Manager: npm
   Test Runner: jest
   Linters: eslint
   Has Build: yes
```

**자동 생성된 YAML (핵심 부분):**
```yaml
jobs:
  lint:
    name: Lint (Node.js)
    steps: [checkout, setup-node, npm ci, npx eslint .]
  test:
    needs: [lint]
    strategy:
      matrix:
        node-version: ["18", "20", "22"]   # ← 자동 matrix
    steps: [checkout, setup-node, npm ci, npx jest --coverage]
  security:
    needs: [test]
    steps: [Semgrep SAST, TruffleHog Secret Scan]  # ← 보안 게이트 기본 포함
```

<!--
실제로 돌려보면 이렇게 나온다.
Node.js 샘플 프로젝트를 스캔하면 package.json에서 jest랑 eslint를 자동으로 감지하고,
lint, test, build, security 순서의 파이프라인을 만들어준다.
여기서 눈여겨볼 건 두 가지인데, Node 버전 18, 20, 22로 matrix strategy를 자동으로 걸어주는 것과,
Semgrep이랑 TruffleHog 같은 보안 게이트가 기본으로 포함된다는 거다.
-->

---

## Key Decisions & Lessons

### 기술 판단

| 판단 | 선택 | 이유 |
|------|------|------|
| 의존성 최소화 | js-yaml + @iarna/toml (2개) | 핵심 기능에 필요한 것만. 템플릿 엔진 대신 js-yaml의 dump로 직접 생성 |
| 감지 규칙 분리 | rules.json 외부 설정 | 코드 수정 없이 에코시스템 추가 가능. 확장성과 유지보수 분리 |
| Python install 커맨드 | `pip install -e ".[dev]"` 폴백 | requirements.txt 없이 pyproject.toml만 있는 프로젝트 대응 (셀프 크리틱에서 발견) |

### 심의 점수와 반대 의견

- 프로토타입 적합성: **4.3/5** — 4시간 안에 완성 가능한 적절한 범위
- 문제 진정성: **3.7/5** — 실제 pain은 있으나 "참을 수 있는" 수준
- 신선도: **2.7/5** — 반대 의견: *"핵심이 파일 존재 확인 + 템플릿 렌더링이며 비자명한 기술적 결정이 없다"*
- 솔직히 맞는 지적이다. 기술적 난이도는 높지 않다. 가치는 **조합의 완성도**에 있다.

<!--
기술 판단에서 꽤 의식적으로 한 게 의존성 최소화다. js-yaml이랑 toml 파서 두 개만 쓴다.
그리고 셀프 크리틱에서 한 가지 잡아낸 게 있는데, Python 프로젝트에서 requirements.txt 없이 pyproject.toml만 있는 경우에 pip install -e 형태로 폴백하도록 수정했다.
심의에서 준혁이 낸 반대 의견이 있었다. 파일 존재 확인이랑 템플릿 렌더링이 전부 아니냐는 건데, 솔직히 맞는 지적이다.
이 프로토타입의 가치는 기술적 난이도가 아니라 조합의 완성도에 있다.
감지, 생성, 검증, 보안 게이트까지 한 번에 엮어서 동작하는 게 핵심이다.
-->

---

## Results & Future

### 성과: 5/5 완료 기준 통과

- [x] 언어/프레임워크/테스트러너/린터 자동 감지
- [x] GitHub Actions YAML 생성 (lint → test → build + matrix strategy)
- [x] 보안 게이트 기본 포함 (Semgrep, TruffleHog)
- [x] validate 명령으로 YAML 문법 검증
- [x] 3개 에코시스템(Node.js, Python, Go) 샘플 데모

### 한계

- GitHub Actions만 지원 — GitLab CI, CircleCI 미지원
- deploy 단계 없음 (클라우드별 인증 연동 필요)
- 3개 에코시스템만 — Rust, Java, Ruby 등 미지원
- 모노레포 미지원 (단일 프로젝트 루트 가정)

### 프로덕트가 되려면

- **에코시스템 확장**: rules.json에 규칙만 추가하면 되는 구조는 갖춰져 있다
- **deploy 단계**: 클라우드 프로바이더별 인증 설정은 인터랙티브 프롬프트가 필요
- **.github/workflows 기존 파일 머지**: 이미 CI가 있는 프로젝트에서의 점진적 개선
- **GitHub App으로 확장**: PR 열릴 때 자동으로 CI 설정 제안

<!--
완료 기준 다섯 개를 모두 통과했고, 빌드 과정에서 에러 없이 첫 시도에 동작했다.
한계는 명확하다. GitHub Actions만 되고, deploy 단계가 없고, 세 개 언어만 지원한다.
다만 rules.json으로 감지 규칙을 분리해놨기 때문에 에코시스템 확장 자체는 어렵지 않다.
실제 프로덕트가 되려면 deploy 단계가 들어가야 하는데, 이건 클라우드 인증 설정이 필요해서 인터랙티브 프롬프트가 빠질 수 없다.
그리고 이미 CI가 있는 프로젝트에서 기존 설정과 머지하는 기능이 있어야 실용적이 된다.
-->
