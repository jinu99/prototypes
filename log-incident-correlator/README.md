# Log-Incident Correlator

> Drain3 기반 first-seen 로그 패턴 탐지와 배포 이벤트 자동 상관관계 분석 프로토타입

## 실행 방법

```bash
# 의존성 설치
uv sync

# 데모 실행 (샘플 데이터 생성 + 분석 + 결과 출력)
uv run python cli.py demo

# 대시보드 실행
uv run python cli.py serve
# → http://localhost:8080
```

## 개별 명령어

```bash
# 로그 파일 파싱
uv run python cli.py ingest <logfile>

# 배포 이벤트 로드 (JSON/CSV)
uv run python cli.py deploys <file>

# 상관관계 분석 (기본 30분 윈도우)
uv run python cli.py correlate --window 30

# 대시보드 서버
uv run python cli.py serve --port 8080
```

## 구조

```
├── cli.py              # CLI 엔트리포인트
├── log_parser.py       # Drain3 기반 로그 템플릿 추출
├── deploy_events.py    # 배포 이벤트 파싱 (JSON/CSV)
├── correlator.py       # 시간 윈도우 상관관계 분석
├── db.py               # SQLite 저장/조회
├── server.py           # 대시보드 HTTP 서버
├── dashboard.html      # 타임라인 시각화 대시보드
├── generate_sample.py  # 샘플 데이터 생성기
├── sample_data/        # 생성된 샘플 데이터
├── BUILD_LOG.md        # 빌드 일지
└── STATUS.md           # 완료 상태
```

## 원본
prototype-pipeline spec: log-incident-correlator
