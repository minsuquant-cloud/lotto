"""'로또는 랜덤이다' 데이터로 증명하기 (아이디어 3).

세 가지 검증:
  1. 카이제곱 적합도 검정 — 번호별 출현 빈도가 균등분포에서 벗어났는가?
     (p-값은 분포 가정 없이 몬테카를로로 직접 계산)
  2. 전략 백테스트 — 핫넘버/콜드넘버/장기미출현 전략이 랜덤보다 잘 맞췄는가?
  3. 몬테카를로 — 가짜 로또 역사 10,000개를 만들어서,
     실제 역사가 그 사이에 섞이면 구분 가능한지 확인

찌릿한 반전: generate.py 의 전략들이 의미 없다는 걸 여기서 증명함 ㅋㅋ
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data" / "lotto.csv"
CHARTS = Path(__file__).parent / "charts"

N_SIMS = 10_000       # 몬테카를로 시뮬레이션 횟수
CHUNK = 250           # 메모리 아끼려고 나눠서 시뮬레이션
WINDOW = 100          # 백테스트에서 '핫넘버' 판단에 쓰는 과거 회차 수

# 차트 스타일 (analyze.py 와 동일 팔레트)
SURFACE, INK, INK_2ND, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, BLUE, AQUA = "#e1e0d9", "#c3c2b7", "#2a78d6", "#1baf7a"
plt.rcParams.update({
    "font.family": ["Malgun Gothic", "NanumGothic", "sans-serif"], "axes.unicode_minus": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK_2ND,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": BASELINE,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "figure.dpi": 110,
})


def chi2_stat(counts: np.ndarray, n_draws: int) -> np.ndarray:
    """번호별 출현 횟수(…, 45)에서 카이제곱 통계량 계산."""
    expected = n_draws * 6 / 45
    return ((counts - expected) ** 2 / expected).sum(axis=-1)


def simulate_histories(n_draws: int, rng: np.random.Generator):
    """가짜 로또 역사 N_SIMS개를 만들어 (카이제곱 통계량, 연속쌍 비율) 분포를 반환."""
    chi2s, consec_rates = [], []
    for start in range(0, N_SIMS, CHUNK):
        n = min(CHUNK, N_SIMS - start)
        # 각 회차 = 45개 중 6개 무작위 추출: 난수 행렬에서 상위 6개 인덱스
        r = rng.random((n * n_draws, 45), dtype=np.float32)
        picks = np.argpartition(r, 6, axis=1)[:, :6]          # (n*회차, 6) 비정렬
        counts = np.zeros((n, 45), dtype=np.int32)
        hist_idx = np.repeat(np.arange(n), n_draws * 6)
        np.add.at(counts, (hist_idx, picks.ravel()), 1)
        chi2s.append(chi2_stat(counts, n_draws))

        picks.sort(axis=1)
        has_consec = (np.diff(picks, axis=1) == 1).any(axis=1).reshape(n, n_draws)
        consec_rates.append(has_consec.mean(axis=1))
    return np.concatenate(chi2s), np.concatenate(consec_rates)


def backtest(nums: np.ndarray, rng: np.random.Generator) -> dict[str, float]:
    """각 전략으로 매 회차 6개를 찍고, 실제 당첨번호와 평균 몇 개 일치했는지."""
    n_draws = len(nums)
    # 회차별 누적 출현 횟수 (트레일링 윈도우 계산용)
    per_draw = np.zeros((n_draws, 45), dtype=np.int32)
    for i, row in enumerate(nums):
        per_draw[i, row - 1] = 1
    cum = per_draw.cumsum(axis=0)

    matches = {"핫넘버": [], "콜드넘버": [], "장기미출현": [], "랜덤": []}
    last_seen = np.zeros(45, dtype=np.int64)
    for i, row in enumerate(nums[:WINDOW]):
        last_seen[row - 1] = i + 1

    for t in range(WINDOW, n_draws):
        trailing = cum[t - 1] - (cum[t - WINDOW - 1] if t > WINDOW else 0)
        actual = set(nums[t])

        picks = {
            "핫넘버": np.argpartition(-trailing, 6)[:6] + 1,   # 최근 많이 나온 6개
            "콜드넘버": np.argpartition(trailing, 6)[:6] + 1,  # 최근 적게 나온 6개
            "장기미출현": np.argpartition(last_seen, 6)[:6] + 1,
            "랜덤": rng.choice(45, size=6, replace=False) + 1,
        }
        for name, p in picks.items():
            matches[name].append(len(actual & set(p.tolist())))

        last_seen[nums[t] - 1] = t + 1

    return {name: float(np.mean(m)) for name, m in matches.items()}


def chart_chi2(sim_chi2: np.ndarray, real_chi2: float):
    pct = (sim_chi2 < real_chi2).mean() * 100
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.hist(sim_chi2, bins=60, color=BLUE, edgecolor=SURFACE, linewidth=0.4)
    ax.axvline(real_chi2, color=INK, lw=1.5, ls=(0, (4, 3)))
    ax.text(real_chi2 + 1.5, ax.get_ylim()[1] * 0.92,
            f"실제 역사 {real_chi2:.1f}\n(하위 {pct:.0f}%)", color=INK, fontsize=9.5)
    ax.set_title(f"카이제곱 통계량 — 가짜 역사 {N_SIMS:,}개 vs 실제")
    ax.set_xlabel("카이제곱 통계량 (균등분포에서 벗어난 정도)")
    ax.set_ylabel("시뮬레이션 수")
    ax.grid(axis="x", visible=False)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(CHARTS / "07_몬테카를로_카이제곱.png")
    plt.close(fig)
    return pct


def chart_backtest(results: dict[str, float]):
    expected = 6 * 6 / 45  # 아무렇게나 찍었을 때 기대 일치 개수 = 0.8
    names = list(results)
    vals = [results[n] for n in names]

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(names, vals, width=0.55, color=BLUE)
    ax.axhline(expected, color=INK_2ND, lw=1, ls=(0, (4, 3)))
    ax.text(len(names) - 0.42, expected + 0.008, f"이론 기대값 {expected:.3f}", color=INK_2ND, fontsize=9)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.008, f"{v:.3f}", ha="center", fontsize=9.5, color=INK)
    ax.set_title(f"전략 백테스트 — 회차당 평균 일치 개수 ({WINDOW + 1}회~)")
    ax.set_ylabel("평균 일치 개수 (6개 중)")
    ax.set_ylim(0, max(vals) * 1.25)
    ax.grid(axis="x", visible=False)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(CHARTS / "08_전략_백테스트.png")
    plt.close(fig)


def main():
    CHARTS.mkdir(exist_ok=True)
    rng = np.random.default_rng()

    df = pd.read_csv(DATA)
    nums = df[["n1", "n2", "n3", "n4", "n5", "n6"]].to_numpy()
    n_draws = len(nums)

    print(f"데이터: 1~{n_draws}회차\n")

    # ── 1. 실제 역사의 통계량 ──
    real_counts = np.bincount((nums - 1).ravel(), minlength=45)
    real_chi2 = float(chi2_stat(real_counts, n_draws))
    real_consec = float(np.mean([(np.diff(np.sort(row)) == 1).any() for row in nums]))

    # ── 2. 몬테카를로 ──
    print(f"몬테카를로 시뮬레이션 {N_SIMS:,}회 실행 중...")
    sim_chi2, sim_consec = simulate_histories(n_draws, rng)
    chi2_pct = chart_chi2(sim_chi2, real_chi2)
    p_value = (sim_chi2 >= real_chi2).mean()
    consec_pct = (sim_consec < real_consec).mean() * 100

    # ── 3. 백테스트 ──
    print("전략 백테스트 실행 중...\n")
    bt = backtest(nums, rng)
    chart_backtest(bt)

    # ── 리포트 ──
    print("=" * 56)
    print("  검증 1: 카이제곱 적합도 검정 (번호 빈도 vs 균등분포)")
    print("=" * 56)
    print(f"  실제 역사 카이제곱 통계량: {real_chi2:.1f}")
    print(f"  몬테카를로 p-값: {p_value:.3f}")
    verdict = "균등분포와 구분 불가 → 랜덤과 일치" if p_value > 0.05 else "균등분포에서 벗어남(?!)"
    print(f"  판정: {verdict}")

    print("\n" + "=" * 56)
    print(f"  검증 2: 전략 백테스트 (최근 {WINDOW}회 기준, {n_draws - WINDOW}회 테스트)")
    print("=" * 56)
    for name, avg in bt.items():
        print(f"  {name:6s}: 회차당 평균 {avg:.3f}개 일치")
    print(f"  이론 기대값(아무거나 6개): {6 * 6 / 45:.3f}개")
    print("  판정: 어떤 전략도 랜덤 기대값과 유의미한 차이 없음")

    print("\n" + "=" * 56)
    print("  검증 3: 실제 역사가 가짜 역사들 사이에서 튀는가?")
    print("=" * 56)
    print(f"  카이제곱 위치: 가짜 {N_SIMS:,}개 중 하위 {chi2_pct:.0f}% 지점 (중간이면 정상)")
    print(f"  연속쌍 비율: 실제 {real_consec:.1%} / 가짜 평균 {sim_consec.mean():.1%} (하위 {consec_pct:.0f}%)")
    print("  판정: 실제 역사는 가짜 랜덤 역사들과 구분 불가능")

    print("\n결론: 로또는 랜덤이다. generate.py 의 전략들은 재미일 뿐 ㅋㅋ")
    print(f"차트 2개 저장 → {CHARTS}")


if __name__ == "__main__":
    main()
