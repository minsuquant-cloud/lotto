"""로또 당첨번호 통계 분석 (아이디어 1).

data/lotto.csv 를 읽어서:
  - 번호별 출현 빈도, 홀짝/구간 분포, 연속번호, 번호 합계
  - 최근 100회 트렌드 vs 전체 역사
콘솔에 요약 출력 + charts/ 폴더에 차트 저장.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

DATA = Path(__file__).parent / "data" / "lotto.csv"
CHARTS = Path(__file__).parent / "charts"

# ── 차트 공통 스타일 (검증된 팔레트) ─────────────────────────
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2ND = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BLUE = "#2a78d6"   # 시리즈 1
AQUA = "#1baf7a"   # 시리즈 2
SEQ_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

plt.rcParams.update({
    # 한글 폰트: 윈도우는 맑은고딕, 리눅스(GitHub Actions)는 나눔고딕으로 폴백
    "font.family": ["Malgun Gothic", "NanumGothic", "sans-serif"],
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK,
    "axes.labelcolor": INK_2ND,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.edgecolor": BASELINE,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "figure.dpi": 110,
})


def style_ax(ax, y_grid_only: bool = True):
    if y_grid_only:
        ax.grid(axis="x", visible=False)
    ax.tick_params(length=0)


def load() -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_csv(DATA, parse_dates=["date"])
    nums = df[["n1", "n2", "n3", "n4", "n5", "n6"]].to_numpy()  # (회차, 6)
    return df, nums


# ── 1. 번호별 출현 빈도 ──────────────────────────────────────
def chart_frequency(nums: np.ndarray) -> pd.Series:
    freq = pd.Series(np.bincount(nums.ravel(), minlength=46)[1:], index=range(1, 46))
    expected = len(nums) * 6 / 45

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.bar(freq.index, freq.values, width=0.72, color=BLUE)
    ax.axhline(expected, color=INK_2ND, lw=1, ls=(0, (4, 3)))
    ax.text(45.4, expected, f"기대값 {expected:.0f}", color=INK_2ND, fontsize=9, va="center")

    # 최다/최소 번호만 선택적 직접 라벨
    for n in [freq.idxmax(), freq.idxmin()]:
        ax.text(n, freq[n] + 4, f"{n}번\n{freq[n]}회", ha="center", fontsize=8.5, color=INK)

    ax.set_title(f"번호별 출현 빈도 (1~{len(nums)}회차, 보너스 제외)")
    ax.set_xlabel("번호")
    ax.set_xticks(range(1, 46, 2))
    ax.set_ylim(0, freq.max() * 1.15)
    ax.margins(x=0.01)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(CHARTS / "01_번호별_빈도.png")
    plt.close(fig)
    return freq


# ── 2. 시대별 히트맵 (100회차 구간 × 번호) ───────────────────
def chart_heatmap(df: pd.DataFrame, nums: np.ndarray):
    bin_size = 100
    bins = (df["draw_no"] - 1) // bin_size
    grid = np.zeros((bins.max() + 1, 45), dtype=float)
    for b, row in zip(bins, nums):
        for n in row:
            grid[b, n - 1] += 1
    # 마지막 구간은 회차 수가 적으므로, 구간별 회차 수로 정규화 (100회당 출현 횟수)
    draws_per_bin = bins.value_counts().sort_index().to_numpy()
    grid = grid / draws_per_bin[:, None] * bin_size

    cmap = LinearSegmentedColormap.from_list("seq_blue", ["#fcfcfb"] + SEQ_RAMP)
    fig, ax = plt.subplots(figsize=(11, 4.8))
    im = ax.imshow(grid, aspect="auto", cmap=cmap, interpolation="nearest")
    ax.set_title("구간별 번호 출현 히트맵 (100회차 단위)")
    ax.set_xlabel("번호")
    ax.set_ylabel("회차 구간")
    ax.set_xticks(range(0, 45, 2), range(1, 46, 2))
    labels = [f"{b * bin_size + 1}~{min((b + 1) * bin_size, df['draw_no'].max())}" for b in range(grid.shape[0])]
    ax.set_yticks(range(grid.shape[0]), labels, fontsize=8)
    ax.grid(visible=False)
    ax.tick_params(length=0)
    cbar = fig.colorbar(im, ax=ax, shrink=0.85, label="100회당 출현 횟수")
    cbar.outline.set_visible(False)
    fig.tight_layout()
    fig.savefig(CHARTS / "02_구간별_히트맵.png")
    plt.close(fig)


# ── 3. 홀수 개수 분포 vs 이론값 ──────────────────────────────
def chart_odd_even(nums: np.ndarray) -> pd.Series:
    odd_counts = pd.Series((nums % 2 == 1).sum(axis=1))
    observed = odd_counts.value_counts(normalize=True).reindex(range(7), fill_value=0)

    # 이론값: 45개 중 홀 23, 짝 22에서 6개 뽑는 초기하분포
    from math import comb
    theory = [comb(23, k) * comb(22, 6 - k) / comb(45, 6) for k in range(7)]

    x = np.arange(7)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(x - 0.19, observed * 100, width=0.36, color=BLUE, label="실제")
    ax.bar(x + 0.19, np.array(theory) * 100, width=0.36, color=AQUA, label="이론(초기하분포)")
    ax.set_title("한 회차의 홀수 개수 분포 — 실제 vs 이론")
    ax.set_xlabel("6개 중 홀수 개수")
    ax.set_ylabel("비율 (%)")
    ax.set_xticks(x, [f"{k}개" for k in x])
    ax.legend(frameon=False)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(CHARTS / "03_홀짝_분포.png")
    plt.close(fig)
    return odd_counts


# ── 4. 구간별 분포 ───────────────────────────────────────────
def chart_ranges(nums: np.ndarray):
    edges = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 45)]
    labels = [f"{a}~{b}" for a, b in edges]
    counts = [((nums >= a) & (nums <= b)).sum() for a, b in edges]
    expected = [len(nums) * 6 * (b - a + 1) / 45 for a, b in edges]

    x = np.arange(len(edges))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(x - 0.19, counts, width=0.36, color=BLUE, label="실제")
    ax.bar(x + 0.19, expected, width=0.36, color=AQUA, label="기대값(균등)")
    ax.set_title("번호 구간별 출현 횟수")
    ax.set_xlabel("번호 구간")
    ax.set_xticks(x, labels)
    ax.legend(frameon=False)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(CHARTS / "04_구간별_분포.png")
    plt.close(fig)


# ── 5. 번호 합계 분포 ────────────────────────────────────────
def chart_sums(nums: np.ndarray) -> pd.Series:
    sums = pd.Series(nums.sum(axis=1))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.hist(sums, bins=range(20, 260, 10), color=BLUE, edgecolor=SURFACE, linewidth=1.5)
    ax.axvline(sums.mean(), color=INK_2ND, lw=1, ls=(0, (4, 3)))
    ax.text(sums.mean() + 3, ax.get_ylim()[1] * 0.95, f"평균 {sums.mean():.0f}", color=INK_2ND, fontsize=9)
    ax.set_title("당첨번호 6개의 합계 분포")
    ax.set_xlabel("합계")
    ax.set_ylabel("회차 수")
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(CHARTS / "05_합계_분포.png")
    plt.close(fig)
    return sums


# ── 6. 최근 100회 vs 전체 ────────────────────────────────────
def chart_recent(nums: np.ndarray, freq_all: pd.Series, recent_n: int = 100) -> pd.Series:
    recent = nums[-recent_n:]
    freq_recent = pd.Series(np.bincount(recent.ravel(), minlength=46)[1:], index=range(1, 46))
    per_draw_all = freq_all / len(nums)          # 전체 역사에서 회차당 출현률
    per_draw_recent = freq_recent / recent_n     # 최근 N회 회차당 출현률

    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.bar(freq_recent.index, per_draw_recent, width=0.72, color=BLUE, label=f"최근 {recent_n}회")
    ax.plot(per_draw_all.index, per_draw_all, color=AQUA, lw=2, label="전체 역사")
    ax.set_title(f"회차당 출현률 — 최근 {recent_n}회 vs 전체")
    ax.set_xlabel("번호")
    ax.set_ylabel("출현률")
    ax.set_xticks(range(1, 46, 2))
    ax.margins(x=0.01)
    ax.legend(frameon=False)
    style_ax(ax)
    fig.tight_layout()
    fig.savefig(CHARTS / "06_최근트렌드.png")
    plt.close(fig)
    return freq_recent


# ── 콘솔 요약 ────────────────────────────────────────────────
def summary(df, nums, freq, odd_counts, sums):
    total = len(nums)
    print(f"\n{'=' * 52}\n  로또 통계 요약  (1~{total}회차, {df['date'].iloc[-1]:%Y-%m-%d} 기준)\n{'=' * 52}")

    top5, bot5 = freq.nlargest(5), freq.nsmallest(5)
    print("\n[출현 빈도]")
    print("  많이 나온 번호:", ", ".join(f"{n}번({c}회)" for n, c in top5.items()))
    print("  적게 나온 번호:", ", ".join(f"{n}번({c}회)" for n, c in bot5.items()))
    print(f"  기대값 {total * 6 / 45:.1f}회 — 최다/최소 편차는 순수 랜덤에서도 이 정도 나옴")

    # 미출현 기간 (마지막 등장 이후 경과 회차)
    last_seen = {n: 0 for n in range(1, 46)}
    for i, row in enumerate(nums):
        for n in row:
            last_seen[n] = i + 1
    overdue = sorted(((total - v, k) for k, v in last_seen.items()), reverse=True)[:5]
    print("\n[장기 미출현]")
    print("  " + ", ".join(f"{n}번({gap}회째 안 나옴)" for gap, n in overdue))

    consec = sum(any(np.diff(sorted(row)) == 1) for row in nums)
    print(f"\n[연속번호] 연속 쌍(예: 14,15) 포함 회차: {consec}회 ({consec / total:.1%})")
    print(f"[홀짝] 평균 홀수 개수: {odd_counts.mean():.2f}개 (이론값 3.07개)")
    print(f"[합계] 평균 {sums.mean():.1f} / 중앙값 {sums.median():.0f} (이론 기대값 138)")


def main():
    CHARTS.mkdir(exist_ok=True)
    df, nums = load()
    freq = chart_frequency(nums)
    chart_heatmap(df, nums)
    odd_counts = chart_odd_even(nums)
    chart_ranges(nums)
    sums = chart_sums(nums)
    chart_recent(nums, freq)
    summary(df, nums, freq, odd_counts, sums)
    print(f"\n차트 6개 저장 완료 → {CHARTS}")


if __name__ == "__main__":
    main()
