# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

동행복권 로또 6/45 당첨번호를 전부 수집해서 통계 분석·번호 생성·랜덤성 증명을 하는 재미 사이드 프로젝트. weinstein_portfolio(로보어드바이저 팀 프로젝트)와는 별개의 개인 놀이터다. 결론은 이미 나와 있다: `prove_random.py`가 "로또는 랜덤이며 어떤 전략도 의미 없다"를 증명했고, 그 위에서 재미로 굴리는 프로젝트다.

## 사용자 스타일

- 반말/친근한 톤 선호, "라온"이라고 부르기
- 코드 수정하면 항상 깃허브에 커밋+푸시 (레포: https://github.com/minsuquant-cloud/lotto.git, main 브랜치)
- **작업 전 `git pull` 필수** — GitHub Actions 봇이 매주 자동 커밋을 넣기 때문

## 자주 쓰는 명령어

```bash
# 가상환경 (Python 3.12, D:\dev\lotto\.venv)
.venv\Scripts\activate
pip install -r requirements.txt   # requests, pandas, matplotlib, numpy, streamlit, plotly

python collect_data.py   # 당첨번호 수집 (증분 — 재실행하면 새 회차만 추가)
python analyze.py        # 통계 분석 + charts/ 에 차트 6종 저장
python generate.py       # 5개 모드 전부, 모드당 5게임 추천
python generate.py balanced -n 10   # 특정 모드만, 게임 수 지정
python generate.py avoid -w 8       # 구간회피형: 최근 8주 기준
python prove_random.py   # 랜덤성 검증 (카이제곱/백테스트/몬테카를로 1만 회)

streamlit run app.py     # 웹앱 → http://localhost:8501
```

테스트 프레임워크·린터는 없다 (재미 프로젝트라 의도적으로 단순하게 유지).

## 아키텍처 (파이프라인 흐름)

```
collect_data.py → data/lotto.csv → analyze.py → charts/*.png
                       ↓
                  generate.py ←── app.py 가 import (MODES, load_stats 등)
                       ↓
                  prove_random.py (전략 무의미함을 증명)
```

- **collect_data.py** — 1순위 동행복권 공식 JSON API, 응답이 JSON이 아니면(간소화 페이지 모드) smok95 GitHub Pages 미러로 자동 폴백. 기존 CSV의 최대 회차 이후만 증분 수집.
- **data/lotto.csv** — 단일 데이터 소스. 컬럼: draw_no, date, n1~n6, bonus, first_prize, first_winners, total_sales. 초기 회차는 미러 데이터라 first_prize 등이 빈 값일 수 있음 (app.py가 fillna로 처리).
- **generate.py** — 번호 생성기 5개 모드: freq(빈도형), contrarian(역발상형), balanced(균형형), avoid(구간회피형, 최근 N주 최다 출현 구간 통째 제외), random(대조군). `MODES` 딕셔너리·`load_stats()`·`ZONES` 등을 app.py가 import하므로 **시그니처 바꿀 때 app.py 동반 수정 필요**.
- **app.py** — Streamlit 웹앱, 탭 6개: 번호 뽑기 / 인생 시뮬(내 번호로 전 회차 백테스트 + "1등 나올 때까지" 시뮬) / 운명의 번호(이름+생일+꿈 SHA-256 시드) / 역대 통계(plotly) / 역대 번호 조회 / 랜덤 증명 요약.
- **analyze.py / prove_random.py** — matplotlib 차트를 charts/ 에 저장. 두 파일이 같은 팔레트 상수(SURFACE, BLUE, AQUA 등)를 각자 정의하고 있으니 스타일 바꿀 땐 양쪽 동기화.

## 자동화 (GitHub Actions)

`.github/workflows/weekly.yml` — 매주 토요일 21:30 KST(추첨 후) + 일요일 08:00 KST 백업 실행. `collect_data.py` → 새 회차 있으면 `analyze.py` → `자동 수집: N회차 반영` 커밋+푸시. 새 회차 없으면 커밋 없이 종료. 수동 실행은 Actions 탭의 workflow_dispatch.

## 알아둘 것

- 동행복권 공식 API는 토요일 추첨 시간대에 "간소화 페이지"로 막힘 → collect_data.py가 미러 폴백으로 자동 대응
- 차트 한글 폰트: 윈도우 맑은고딕, 리눅스(CI)는 나눔고딕 폴백 — weekly.yml이 fonts-nanum을 설치함
- CI Python은 3.12 (weekly.yml), 로컬 .venv도 3.12
