# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 로또 프로젝트

동행복권 로또 6/45 당첨번호를 수집·분석하는 재미 사이드 프로젝트.
weinstein_portfolio(로보어드바이저 팀 프로젝트)와 별개의 개인 놀이터.

## 사용자 스타일

- 반말/친근한 톤 선호, 사용자를 "형님"이라고 부를 것
- 코드 수정하면 항상 깃허브에 커밋+푸시 (레포: https://github.com/minsuquant-cloud/lotto.git, main 브랜치)
- 데이터는 직접 크롤링하는 것 선호
- 커밋 메시지는 한국어로 작성 (기존 히스토리 참고)

## 명령어

```bash
python -m venv .venv && .venv\Scripts\activate   # 윈도우 (리눅스: source .venv/bin/activate)
pip install -r requirements.txt                  # requests, pandas, matplotlib, numpy

python collect_data.py            # 데이터 수집 — 증분식, 재실행하면 새 회차만 추가
python analyze.py                 # 통계 분석 + charts/에 차트 6종 생성
python generate.py                # 번호 생성 — 5개 모드 전부, 모드당 5게임
python generate.py balanced -n 10 # 특정 모드만: freq/contrarian/balanced/avoid/random
python generate.py avoid -w 8     # 구간회피형이 보는 최근 주 수 지정
python prove_random.py            # 랜덤성 검증 — 몬테카를로 1만 회, 1~2분 소요
```

테스트/린터는 없음. 검증은 스크립트를 직접 실행해서 출력과 차트를 확인하는 방식.

## 아키텍처

파이프라인: `collect_data.py` → `data/lotto.csv` → 나머지 스크립트 전부가 이 CSV 하나를 읽음.

- **`collect_data.py`** — 수집기. 동행복권 공식 JSON API 우선, 응답이 JSON이 아니면(간소화 페이지 모드) smok95 GitHub Pages 미러로 자동 폴백. 기존 CSV의 최대 회차 이후만 증분 수집.
- **`data/lotto.csv`** — 단일 데이터 소스. 컬럼: `draw_no, date, n1~n6(정렬됨), bonus, first_prize, first_winners, total_sales`. 스키마 바꾸면 아래 세 스크립트 다 영향받음.
- **`analyze.py`** — 통계 요약(콘솔) + `charts/`에 차트 6종 (빈도, 히트맵, 홀짝, 구간, 합계, 최근 트렌드).
- **`generate.py`** — 번호 생성기 5개 모드. `MODES` 딕셔너리(`이름 → (설명, 생성함수)`)에 등록하는 구조라 모드 추가 시 `gen_*` 함수 작성 후 여기에 한 줄 추가. 생성함수는 공통으로 `Stats` 데이터클래스를 받음.
- **`prove_random.py`** — 랜덤성 검증 3종: 카이제곱(p-값은 몬테카를로로 직접 계산), 전략 백테스트(핫/콜드/장기미출현 vs 랜덤), 가짜 역사 1만 개 비교. 결론: 로또는 랜덤이고 generate.py의 전략들은 재미일 뿐.
- **`.github/workflows/weekly.yml`** — 매주 토요일 추첨 후(21:30 KST, 백업 일요일 08:00 KST) 자동 수집 → 새 회차 있으면 분석 갱신 → `data`+`charts` 자동 커밋("자동 수집: N회차 반영").

## 컨벤션

- 주석·docstring·차트 라벨·콘솔 출력 전부 한국어
- 차트 스타일: `analyze.py`와 `prove_random.py`가 동일한 색 팔레트/rcParams 공유 (SURFACE/INK/BLUE/AQUA 등). 새 차트도 이 팔레트를 따를 것
- 한글 폰트: 윈도우 맑은고딕, 리눅스(GitHub Actions) 나눔고딕 폴백 — `font.family` 리스트로 처리됨
- 차트 파일명은 `NN_한글이름.png` 순번 형식 (현재 01~08)
- README.md에 구성표·사용법·주요 결과가 정리돼 있으니, 기능 추가/변경 시 README도 같이 갱신

## 알아둘 것

- 동행복권 공식 API는 토요일 추첨 시간대에 "간소화 페이지"로 막힘 → collect_data.py가 자동으로 미러 폴백하므로 별도 대응 불필요
- `data/lotto.csv`와 `charts/`는 GitHub Actions 봇이 매주 자동 커밋함 — 로컬 작업 전에 pull 먼저
- 모든 조합의 당첨 확률은 1/8,145,060으로 동일. 생성기는 어디까지나 재미 (prove_random.py가 증명함)
