"""통계 기반 로또 번호 생성기 (아이디어 2).

4가지 모드:
  freq        빈도형   — 역대 많이 나온 번호에 가중치
  contrarian  역발상형 — 적게 나온 번호 + 오래 안 나온 번호에 가중치
  balanced    균형형   — 홀짝·구간·합계가 역대 당첨 분포의 중심부에 들도록
  random      완전랜덤 — 대조군

사용법:
  python generate.py              # 4개 모드 전부, 모드당 5게임
  python generate.py balanced     # 균형형만 5게임
  python generate.py freq -n 10   # 빈도형 10게임

※ 재미로 만든 것. 아이디어 3에서 이 생성기가 의미 없다는 걸 스스로 증명할 예정 ㅋㅋ
"""

import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data" / "lotto.csv"
NUMBERS = list(range(1, 46))


def load_stats() -> tuple[pd.Series, pd.Series, int]:
    """번호별 출현 횟수, 마지막 출현 이후 경과 회차, 최신 회차 번호를 반환."""
    df = pd.read_csv(DATA)
    nums = df[["n1", "n2", "n3", "n4", "n5", "n6"]].to_numpy()
    freq = pd.Series(np.bincount(nums.ravel(), minlength=46)[1:], index=NUMBERS)

    last_seen = pd.Series(0, index=NUMBERS)
    for i, row in enumerate(nums, start=1):
        last_seen[list(row)] = i
    gap = len(nums) - last_seen  # 몇 회째 안 나왔는지
    return freq, gap, int(df["draw_no"].max())


def pick_weighted(weights: pd.Series) -> list[int]:
    """가중치에 비례해 중복 없이 6개 뽑기."""
    p = (weights / weights.sum()).values
    return sorted(np.random.choice(NUMBERS, size=6, replace=False, p=p).tolist())


def gen_freq(freq: pd.Series, gap: pd.Series) -> list[int]:
    """빈도형: 출현 횟수에 비례한 가중치."""
    return pick_weighted(freq.astype(float))


def gen_contrarian(freq: pd.Series, gap: pd.Series) -> list[int]:
    """역발상형: 덜 나온 번호(역빈도) + 오래 안 나온 번호(경과 회차) 가중치."""
    inv_freq = freq.max() - freq + 1          # 덜 나올수록 큼
    overdue = gap + 1                          # 오래 안 나올수록 큼
    # 두 신호를 각각 0~1로 정규화해서 합산
    w = inv_freq / inv_freq.max() + overdue / overdue.max()
    return pick_weighted(w)


def gen_balanced(freq: pd.Series, gap: pd.Series) -> list[int]:
    """균형형: 균등 추출을 반복하되 역대 당첨 분포의 중심부 조건을 만족할 때까지.

    조건 (역대 데이터에서 대다수 회차가 만족하는 범위):
      - 홀수 2~4개
      - 합계 100~175 (역대 중앙 70% 구간)
      - 구간(1~10/11~20/21~30/31~40/41~45) 최소 3개에 분산
      - 같은 구간에 4개 이상 몰리지 않기
    """
    while True:
        picks = sorted(random.sample(NUMBERS, 6))
        odd = sum(n % 2 for n in picks)
        if not 2 <= odd <= 4:
            continue
        if not 100 <= sum(picks) <= 175:
            continue
        zones = [min((n - 1) // 10, 4) for n in picks]
        counts = np.bincount(zones, minlength=5)
        if (counts > 0).sum() < 3 or counts.max() >= 4:
            continue
        return picks


def gen_random(freq: pd.Series, gap: pd.Series) -> list[int]:
    """완전랜덤: 대조군."""
    return sorted(random.sample(NUMBERS, 6))


MODES = {
    "freq": ("빈도형 — 많이 나온 번호 위주", gen_freq),
    "contrarian": ("역발상형 — 이제 나올 때 됐다", gen_contrarian),
    "balanced": ("균형형 — 역대 당첨 분포 닮은꼴", gen_balanced),
    "random": ("완전랜덤 — 대조군", gen_random),
}


def main():
    parser = argparse.ArgumentParser(description="통계 기반 로또 번호 생성기")
    parser.add_argument("mode", nargs="?", default="all", choices=[*MODES, "all"])
    parser.add_argument("-n", "--games", type=int, default=5, help="게임 수 (기본 5)")
    args = parser.parse_args()

    freq, gap, latest = load_stats()
    modes = MODES if args.mode == "all" else {args.mode: MODES[args.mode]}

    print(f"\n🎱 이번 주 추천 번호 ({latest}회차까지 데이터 기준)\n")
    for key, (desc, fn) in modes.items():
        print(f"[{key}] {desc}")
        for i in range(args.games):
            picks = fn(freq, gap)
            print(f"  {chr(65 + i)}게임:  " + "  ".join(f"{n:2d}" for n in picks))
        print()
    print("※ 어디까지나 재미! 모든 조합의 당첨 확률은 똑같이 1/8,145,060 이야.")


if __name__ == "__main__":
    main()
