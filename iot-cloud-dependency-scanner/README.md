# IoT Cloud Dependency Scanner

> 홈 네트워크의 IoT 기기를 자동 발견하고 DNS 트래픽 분석으로 클라우드 의존도를 정량화하여, 실행 가능한 로컬 대안을 제시하는 진단 도구

## 실행 방법

```bash
# 의존성 설치
uv sync

# 데모 모드 (mock 데이터, root 불필요)
uv run python cli.py run --demo

# 실제 네트워크 스캔 (root 필요)
sudo uv run python cli.py run -i eth0 -n 192.168.1.0/24

# 개별 단계 실행
uv run python cli.py scan --demo        # 기기 탐색만
uv run python cli.py capture --demo     # DNS 캡처만
uv run python cli.py report             # 리포트 생성만
```

## 주요 기능

- **기기 발견**: ARP 스캔 + mDNS/SSDP 탐색으로 네트워크 내 IoT 기기 자동 발견
- **제조사 식별**: MAC OUI 데이터베이스 기반 (70+ OUI 등록)
- **DNS 트래픽 분석**: Passive DNS 캡처로 각 기기의 클라우드 엔드포인트 매핑
- **의존도 점수**: DNS 쿼리 빈도 + 목적지 다양성 + 클라우드 비율 기반 0-100 점수
- **로컬 대안 제안**: 19개 인기 제조사에 대한 자체 호스팅/로컬 대안 매핑
- **HTML 리포트**: 단일 파일 dark-theme 리포트 (report.html)

## 구조

```
iot-cloud-dependency-scanner/
├── cli.py              # CLI 진입점 (scan/capture/report/run)
├── scanner.py          # 기기 탐색 (ARP, mDNS, SSDP)
├── dns_capture.py      # Passive DNS 캡처
├── analyzer.py         # 클라우드 의존도 분석 및 점수 산출
├── report.py           # CLI + HTML 리포트 생성
├── oui_db.py           # MAC OUI → 제조사 매핑 DB
├── alternatives_db.py  # 제조사 → 로컬 대안 매핑 DB
├── demo_data.py        # 데모용 mock 데이터
├── data/               # 스캔/캡처 결과 저장
├── report.html         # 생성된 HTML 리포트
├── BUILD_LOG.md        # 빌드 일지
└── STATUS.md           # 프로토타입 상태
```

## 원본
prototype-pipeline spec: iot-cloud-dependency-scanner
