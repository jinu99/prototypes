# Build Log

## Phase 1 — Spec 확인
- [시작] 2026-03-10 — Spec 파일 확인 완료
- [범위] CLI 도구 `ci-gen init`으로 프로젝트 디렉토리 스캔 → GitHub Actions YAML 자동 생성
- [완료기준] 5개 항목: 자동감지, YAML생성, 보안게이트, validate 명령, 3개 에코시스템 데모
- [판단] 스택 선택: Node.js + npm (이유: Spec에 "Node.js 기반" 명시, js-yaml로 YAML 생성/검증 통합 가능)
- [판단] 핵심 의존성: js-yaml (YAML 생성/파싱), @iarna/toml (pyproject.toml 파싱) — 총 2개로 최소화
- [판단] 구조: 감지 규칙을 JSON 설정(rules.json)으로 분리하여 확장 가능한 아키텍처

## Phase 2 — 구현
- [시도] npm init + js-yaml, @iarna/toml 설치 → [결과] 성공
- [시도] rules.json 감지 규칙 설정 파일 작성 → [결과] 성공 (3개 에코시스템 × 패키지매니저/테스터/린터 매핑)
- [시도] detector.js — package.json, pyproject.toml, go.mod 파싱 → [결과] 성공
- [시도] generator.js — 감지 결과 → GitHub Actions YAML 변환 → [결과] 성공 (lint→test→build→security 파이프라인)
- [시도] validator.js — YAML 문법 + GitHub Actions 스키마 검증 → [결과] 성공
- [시도] cli.js — init/validate/detect 서브커맨드 구현 → [결과] 성공
- [시도] 3개 샘플 프로젝트 (node/python/go) 생성 후 테스트 → [결과] 성공
- 반복 횟수: 1회 (에러 없이 첫 시도에 동작)

## Phase 3 — 셀프 크리틱
- [평가] "이걸 누가 보면?" → "오 되네" 쪽. CLI 출력이 깔끔하고 생성된 YAML이 실제 사용 가능한 수준
- [평가] Spec 검증 목표 → 모두 충족. 자동 감지가 정확하고, YAML 구조가 GitHub Actions 표준 따름
- [평가] 출력 깔끔함 → YAML 포맷 양호. `"on"` 따옴표는 js-yaml 특성이자 올바른 동작 (YAML 1.1 boolean 회피)
- [불만] Python 프로젝트에서 `pip install -r requirements.txt`로 생성되나, pyproject.toml만 있는 프로젝트에선 부적절
- [개선] requirements.txt 없을 때 `pip install -e ".[dev]"` 형태로 optional-dependencies 그룹 자동 포함하도록 수정
- [재검증] Python 샘플에서 `pip install -e ".[dev]"` 정상 출력 확인
- 개선 루프 횟수: 1회

## Phase 4 — 검증
- [체크] 기준1: ci-gen init으로 언어/프레임워크/테스트러너/린터 감지 → 통과 (3개 에코시스템 모두 정확)
- [체크] 기준2: GitHub Actions YAML 생성 (lint→test→build) → 통과 (needs 체인 + matrix strategy 포함)
- [체크] 기준3: 보안 게이트 (Semgrep, TruffleHog) 기본 포함 → 통과
- [체크] 기준4: validate 명령으로 YAML 문법 검증 → 통과 (valid/invalid 모두 정확히 판별)
- [체크] 기준5: 3개 에코시스템 샘플 정상 동작 데모 → 통과

결과: **5/5 통과 — SUCCESS**
