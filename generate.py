"""통계 기반 로또 번호 생성기 (아이디어 2).

5가지 모드:
  freq        빈도형     — 역대 많이 나온 번호에 가중치
  contrarian  역발상형   — 적게 나온 번호 + 오래 안 나온 번호에 가중치
  balanced    균형형     — 홀짝·구간·합계가 역대 당첨 분포의 중심부에 들도록
  avoid       구간회피형 — 최근 N주 당첨번호가 몰린 구간(1~10, 11~20...)을 통째로 제외
  random      완전랜덤   — 대조군

사용법:
  python generate.py              # 5개 모드 전부, 모드당 5게임
  python generate.py balanced     # 균형형만 5게임
  python generate.py freq -n 10   # 빈도형 10게임
  python generate.py avoid -w 8   # 구간회피형, 최근 8주 기준

※ 재미로 만든 것. prove_random.py 가 이 전략들이 의미 없다는 걸 이미 증명함 ㅋㅋ
"""

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data" / "lotto.csv"
NUMBERS = list(range(1, 46))
ZONES = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 45)]


def zone_of(n: int) -> int:
    return min((n - 1) // 10, 4)


@dataclass
class Stats:
    freq: pd.Series        # 번호별 역대 출현 횟수
    gap: pd.Series         # 마지막 출현 이후 경과 회차
    latest: int            # 최신 회차 번호
    zone_counts: list[int] # 최근 N주 구간별 출현 횟수
    hot_zones: set[int]    # 최근 N주 최다 출현 구간 (동률 포함)
    weeks: int             # 구간 집계에 쓴 주 수


def load_stats(weeks: int) -> Stats:
    df = pd.read_csv(DATA)
    nums = df[["n1", "n2", "n3", "n4", "n5", "n6"]].to_numpy()
    freq = pd.Series(np.bincount(nums.ravel(), minlength=46)[1:], index=NUMBERS)

    last_seen = pd.Series(0, index=NUMBERS)
    for i, row in enumerate(nums, start=1):
        last_seen[list(row)] = i
    gap = len(nums) - last_seen

    recent = nums[-weeks:]
    zone_counts = [0] * 5
    for n in recent.ravel():
        zone_counts[zone_of(n)] += 1
    top = max(zone_counts)
    hot_zones = {z for z, c in enumerate(zone_counts) if c == top}

    return Stats(freq, gap, int(df["draw_no"].max()), zone_counts, hot_zones, weeks)


def pick_weighted(weights: pd.Series) -> list[int]:
    """가중치에 비례해 중복 없이 6개 뽑기."""
    p = (weights / weights.sum()).values
    return sorted(np.random.choice(NUMBERS, size=6, replace=False, p=p).tolist())


def gen_freq(st: Stats) -> list[int]:
    """빈도형: 출현 횟수에 비례한 가중치."""
    return pick_weighted(st.freq.astype(float))


def gen_contrarian(st: Stats) -> list[int]:
    """역발상형: 덜 나온 번호(역빈도) + 오래 안 나온 번호(경과 회차) 가중치."""
    inv_freq = st.freq.max() - st.freq + 1
    overdue = st.gap + 1
    w = inv_freq / inv_freq.max() + overdue / overdue.max()
    return pick_weighted(w)


def gen_balanced(st: Stats) -> list[int]:
    """균형형: 균등 추출을 반복하되 역대 당첨 분포의 중심부 조건을 만족할 때까지.

    조건: 홀수 2~4개, 합계 100~175, 3개 이상 구간에 분산, 한 구간에 4개 이상 금지.
    """
    while True:
        picks = sorted(random.sample(NUMBERS, 6))
        odd = sum(n % 2 for n in picks)
        if not 2 <= odd <= 4:
            continue
        if not 100 <= sum(picks) <= 175:
            continue
        counts = np.bincount([zone_of(n) for n in picks], minlength=5)
        if (counts > 0).sum() < 3 or counts.max() >= 4:
            continue
        return picks


def gen_avoid(st: Stats) -> list[int]:
    """구간회피형: 최근 N주 당첨번호가 가장 많이 나온 구간의 숫자를 전부 제외하고 균등 추출."""
    pool = [n for n in NUMBERS if zone_of(n) not in st.hot_zones]
    return sorted(random.sample(pool, 6))


def gen_random(st: Stats) -> list[int]:
    """완전랜덤: 대조군."""
    return sorted(random.sample(NUMBERS, 6))


MODES = {
    "freq": ("빈도형 — 많이 나온 번호 위주", gen_freq),
    "contrarian": ("역발상형 — 이제 나올 때 됐다", gen_contrarian),
    "balanced": ("균형형 — 역대 당첨 분포 닮은꼴", gen_balanced),
    "avoid": ("구간회피형 — 최근 뜨거웠던 열은 피한다", gen_avoid),
    "random": ("완전랜덤 — 대조군", gen_random),
}


def zone_label(z: int) -> str:
    a, b = ZONES[z]
    return f"{a}~{b}"


def main():
    parser = argparse.ArgumentParser(description="통계 기반 로또 번호 생성기")
    parser.add_argument("mode", nargs="?", default="all", choices=[*MODES, "all"])
    parser.add_argument("-n", "--games", type=int, default=5, help="게임 수 (기본 5)")
    parser.add_argument("-w", "--weeks", type=int, default=5, help="구간회피형이 보는 최근 주 수 (기본 5)")
    args = parser.parse_args()

    st = load_stats(args.weeks)
    modes = MODES if args.mode == "all" else {args.mode: MODES[args.mode]}

    print(f"\n🎱 이번 주 추천 번호 ({st.latest}회차까지 데이터 기준)\n")
    for key, (desc, fn) in modes.items():
        print(f"[{key}] {desc}")
        if key == "avoid":
            dist = ", ".join(f"{zone_label(z)}:{c}개" for z, c in enumerate(st.zone_counts))
            excluded = ", ".join(zone_label(z) for z in sorted(st.hot_zones))
            print(f"  (최근 {st.weeks}주 구간 분포 → {dist})")
            print(f"  (제외 구간: {excluded})")
        for i in range(args.games):
            picks = fn(st)
            print(f"  {chr(65 + i)}게임:  " + "  ".join(f"{n:2d}" for n in picks))
        print()
    print("※ 어디까지나 재미! 모든 조합의 당첨 확률은 똑같이 1/8,145,060 이야.")


if __name__ == "__main__":
    main()
