# STATUS: SUCCESS

## 요약
인디 개발자용 매출 어트리뷰션 대시보드. Stripe webhook으로 결제를 수신하고, UTM 세션 데이터와 매칭하여 채널별 매출 기여도/ROI/진짜 CAC를 한 화면에 시각화한다.

## 완료 기준 결과
- [x] Stripe Test Mode webhook으로 결제 이벤트를 수신하고 SQLite에 저장
- [x] Umami/Plausible API에서 UTM 세션 데이터를 가져와 결제 이벤트와 매칭
- [x] 채널별 매출 기여도 + ROI를 한 화면에 시각화하는 대시보드
- [x] 시간/도구 비용을 포함한 '진짜 CAC' 계산 결과가 채널별로 표시
- [x] 샘플 데이터(5개 채널, 20건 결제)로 end-to-end 데모 동작

## 실행 방법
README.md 참조

## 소요 정보
- 생성일: 2026-03-19
- 원본 spec: indie-revenue-attribution.md
- 자동 생성: prototype-pipeline spawn
