"""로또 데이터 놀이터 — Streamlit 웹앱.

실행:  streamlit run app.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from generate import MODES, ZONES, load_stats, zone_label, zone_of

# ── 팔레트 ───────────────────────────────────────────────────
BLUE, AQUA = "#2a78d6", "#1baf7a"
INK_2ND, MUTED, GRID = "#52514e", "#898781", "#e1e0d9"

# 동행복권 공식 볼 색상 (1~10 노랑, 11~20 파랑, 21~30 빨강, 31~40 회색, 41~45 초록)
BALL_COLORS = ["#fbc400", "#69c8f2", "#ff7272", "#aaaaaa", "#b0d840"]

st.set_page_config(page_title="로또 데이터 놀이터", page_icon="🎱", layout="centered")


@st.cache_data
def load_df() -> pd.DataFrame:
    return pd.read_csv("data/lotto.csv", parse_dates=["date"])


def balls_html(numbers, bonus=None, size=38) -> str:
    """당첨번호를 실제 로또볼 모양으로 렌더링."""
    ball = (
        "<span style='display:inline-block;width:{s}px;height:{s}px;border-radius:50%;"
        "background:{c};color:#fff;text-align:center;line-height:{s}px;"
        "font-weight:700;font-size:{f}px;margin:2px;"
        "text-shadow:0 1px 2px rgba(0,0,0,.35);"
        "box-shadow:inset -3px -3px 6px rgba(0,0,0,.18)'>{n}</span>"
    )
    html = "".join(ball.format(s=size, f=int(size * 0.42), c=BALL_COLORS[zone_of(n)], n=n) for n in numbers)
    if bonus is not None:
        html += f"<span style='margin:0 6px;color:{MUTED};font-size:{int(size*0.5)}px'>+</span>"
        html += ball.format(s=size, f=int(size * 0.42), c=BALL_COLORS[zone_of(bonus)], n=bonus)
    return html


def base_layout(fig: go.Figure, height=360):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Malgun Gothic, sans-serif", color=INK_2ND),
        margin=dict(l=10, r=10, t=36, b=10),
        hoverlabel=dict(font_family="Malgun Gothic, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(gridcolor=GRID, linecolor=GRID, tickcolor="rgba(0,0,0,0)")
    fig.update_yaxes(gridcolor=GRID, linecolor="rgba(0,0,0,0)", tickcolor="rgba(0,0,0,0)")
    return fig


df = load_df()
nums = df[["n1", "n2", "n3", "n4", "n5", "n6"]].to_numpy()
latest = df.iloc[-1]

# ── 헤더: 최신 회차 ──────────────────────────────────────────
st.title("🎱 로또 데이터 놀이터")
st.caption(f"1~{int(latest['draw_no'])}회차 데이터 · 매주 토요일 밤 자동 갱신")

with st.container(border=True):
    st.markdown(
        f"**{int(latest['draw_no'])}회** · {latest['date']:%Y-%m-%d} · "
        f"1등 {int(latest['first_winners'])}명 (각 {int(latest['first_prize']) / 1e8:.1f}억)"
    )
    st.markdown(balls_html([latest[f"n{i}"] for i in range(1, 7)], bonus=latest["bonus"]), unsafe_allow_html=True)

tab_gen, tab_stats, tab_history, tab_proof = st.tabs(["🎰 번호 뽑기", "📊 역대 통계", "📜 역대 번호", "⚖️ 랜덤 증명"])

# ── 탭 1: 번호 뽑기 ──────────────────────────────────────────
with tab_gen:
    mode_names = {
        "freq": "빈도형 — 많이 나온 번호 위주",
        "contrarian": "역발상형 — 이제 나올 때 됐다",
        "balanced": "균형형 — 역대 당첨 분포 닮은꼴",
        "avoid": "구간회피형 — 최근 뜨거웠던 열은 피한다",
        "random": "완전랜덤 — 대조군",
    }
    mode = st.radio("전략", list(mode_names), format_func=mode_names.get, index=3)

    col1, col2 = st.columns(2)
    n_games = col1.slider("게임 수", 1, 10, 5)
    weeks = col2.slider("구간회피형: 최근 몇 주를 볼까", 3, 20, 5) if mode == "avoid" else 5

    stats = load_stats(weeks)

    if mode == "avoid":
        dist = " · ".join(f"{zone_label(z)}: **{c}개**" for z, c in enumerate(stats.zone_counts))
        excluded = ", ".join(zone_label(z) for z in sorted(stats.hot_zones))
        st.info(f"최근 {weeks}주 구간 분포 → {dist}\n\n🚫 제외 구간: **{excluded}**")

    if st.button("번호 뽑기 🎲", type="primary", use_container_width=True):
        _, fn = MODES[mode]
        for i in range(n_games):
            picks = fn(stats)
            c1, c2 = st.columns([1, 9])
            c1.markdown(f"<div style='line-height:42px;color:{MUTED}'>{chr(65 + i)}게임</div>", unsafe_allow_html=True)
            c2.markdown(balls_html(picks), unsafe_allow_html=True)
        st.caption("※ 어디까지나 재미! 모든 조합의 당첨 확률은 똑같이 1/8,145,060")

# ── 탭 2: 역대 통계 ──────────────────────────────────────────
with tab_stats:
    freq = pd.Series(np.bincount(nums.ravel(), minlength=46)[1:], index=range(1, 46))
    expected = len(nums) * 6 / 45

    st.subheader("번호별 출현 빈도")
    fig = go.Figure(go.Bar(
        x=list(freq.index), y=freq.values, marker_color=BLUE,
        hovertemplate="%{x}번 · %{y}회<extra></extra>",
    ))
    fig.add_hline(y=expected, line_dash="dash", line_color=INK_2ND, line_width=1,
                  annotation_text=f"기대값 {expected:.0f}", annotation_font_color=INK_2ND)
    st.plotly_chart(base_layout(fig), use_container_width=True)

    st.subheader("최근 흐름 vs 전체 역사")
    recent_n = st.slider("최근 몇 회를 볼까", 20, 300, 100, step=10)
    freq_recent = pd.Series(np.bincount(nums[-recent_n:].ravel(), minlength=46)[1:], index=range(1, 46))
    fig = go.Figure([
        go.Bar(x=list(freq_recent.index), y=freq_recent / recent_n, name=f"최근 {recent_n}회",
               marker_color=BLUE, hovertemplate="%{x}번 · 회차당 %{y:.3f}<extra></extra>"),
        go.Scatter(x=list(freq.index), y=freq / len(nums), name="전체 역사",
                   line=dict(color=AQUA, width=2), hovertemplate="%{x}번 · 회차당 %{y:.3f}<extra></extra>"),
    ])
    fig.update_yaxes(title="회차당 출현률")
    st.plotly_chart(base_layout(fig), use_container_width=True)

    st.subheader("번호 합계 분포")
    sums = nums.sum(axis=1)
    fig = go.Figure(go.Histogram(
        x=sums, xbins=dict(start=20, end=260, size=10), marker_color=BLUE,
        marker_line=dict(color="rgba(0,0,0,0)", width=1),
        hovertemplate="합계 %{x} · %{y}회차<extra></extra>",
    ))
    fig.add_vline(x=float(sums.mean()), line_dash="dash", line_color=INK_2ND, line_width=1,
                  annotation_text=f"평균 {sums.mean():.0f}", annotation_font_color=INK_2ND)
    st.plotly_chart(base_layout(fig, height=320), use_container_width=True)

    st.subheader("구간별 출현 (실제 vs 균등 기대값)")
    z_counts = [((nums >= a) & (nums <= b)).sum() for a, b in ZONES]
    z_exp = [len(nums) * 6 * (b - a + 1) / 45 for a, b in ZONES]
    labels = [zone_label(z) for z in range(5)]
    fig = go.Figure([
        go.Bar(x=labels, y=z_counts, name="실제", marker_color=BLUE,
               hovertemplate="%{x} · %{y}회<extra></extra>"),
        go.Bar(x=labels, y=z_exp, name="기대값(균등)", marker_color=AQUA,
               hovertemplate="%{x} · %{y:.0f}회<extra></extra>"),
    ])
    st.plotly_chart(base_layout(fig, height=320), use_container_width=True)

# ── 탭 3: 역대 번호 ──────────────────────────────────────────
with tab_history:
    st.subheader("회차 조회")
    drw = st.number_input("회차 번호", 1, int(latest["draw_no"]), int(latest["draw_no"]))
    row = df[df["draw_no"] == drw].iloc[0]
    with st.container(border=True):
        prize = f" · 1등 {int(row['first_winners'])}명 (각 {int(row['first_prize']) / 1e8:.1f}억)" if row["first_winners"] > 0 else ""
        st.markdown(f"**{drw}회** · {row['date']:%Y-%m-%d}{prize}")
        st.markdown(balls_html([row[f"n{i}"] for i in range(1, 7)], bonus=row["bonus"]), unsafe_allow_html=True)

    st.subheader("전체 목록")
    show = df.sort_values("draw_no", ascending=False).copy()
    show["date"] = show["date"].dt.strftime("%Y-%m-%d")
    show["당첨번호"] = show[[f"n{i}" for i in range(1, 7)]].astype(str).agg(", ".join, axis=1)
    show["1등 당첨금(억)"] = (show["first_prize"].fillna(0) / 1e8).round(1)
    st.dataframe(
        show[["draw_no", "date", "당첨번호", "bonus", "first_winners", "1등 당첨금(억)"]].rename(columns={
            "draw_no": "회차", "date": "날짜", "bonus": "보너스", "first_winners": "1등 수",
        }),
        use_container_width=True, hide_index=True, height=420,
    )

# ── 탭 4: 랜덤 증명 ──────────────────────────────────────────
with tab_proof:
    st.subheader("결론: 로또는 랜덤이다 ⚖️")
    st.markdown(
        """
1. **카이제곱 검정** — 번호별 빈도의 치우침은 몬테카를로 p-값 **0.92**.
   완전 랜덤이 만드는 치우침보다 오히려 *더 고른* 편.
2. **전략 백테스트** (1,130회) — 핫넘버 0.800 / 콜드넘버 0.788 / 장기미출현 0.781 / 랜덤 0.802개 일치.
   이론 기대값 0.800 근처에서 도토리 키재기.
3. **몬테카를로** — 가짜 역사 10,000개 사이에 실제 역사를 섞으면 **구분 불가능**.

그러니까 옆 탭의 생성기는 전부 재미용 ㅋㅋ 자세한 건 `python prove_random.py`
"""
    )
    st.image("charts/07_몬테카를로_카이제곱.png")
    st.image("charts/08_전략_백테스트.png")
