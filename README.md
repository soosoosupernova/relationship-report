# 관계 패턴 리포트

16문항으로 애착불안·애착회피 두 축과 관계 해석 습관, 갈등 대응 행동을 살펴보는 자기이해 리포트.

## 배포 위치
- 서비스 URL: https://soosoosupernova.github.io/relationship-report/
- 실제 배포는 루트 저장소 `soosoosupernova/soosoosupernova.github.io`의 `relationship-report/` 폴더에서 이루어집니다.
  (GitHub App 연결 권한으로는 저장소 Pages API를 켤 수 없어 루트 사이트 하위 폴더 방식으로 배포했습니다.)
- 이 저장소는 원본 보관용입니다. 이 저장소에서 Pages를 켜면 같은 URL이 겹치므로, 이쪽을 배포 원본으로 쓰려면
  루트 저장소의 `relationship-report/` 폴더를 지우고 Settings → Pages에서 main / 를 지정하세요.

## 구성
- `index.html` — HTML·CSS·JS 단일 파일 (base64 이미지 없음, 41KB)
- `assets/practice-hero.webp` (88KB) · `assets/favicon.svg` · `og-image.png` (1200×630)

## 검증
    python3 verify_v6.py     # QuickJS + 미니 DOM, 73개 체크 (광고 게이트 7흐름·퀴즈·극단 응답)
