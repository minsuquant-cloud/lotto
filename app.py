"""로또 데이터 놀이터 — Streamlit 웹앱.

실행:  streamlit run app.py
"""

import hashlib
import random
import time
from datetime import date

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

# 등수별 상금 (1등은 실제 회차 데이터 사용, 나머지는 평균 추정치)
PRIZE = {2: 55_000_000, 3: 1_550_000, 4: 50_000, 5: 5_000}
TICKET = 1_000  # 게임당 가격
COMBOS = 8_145_060
# 게임 1장의 등수별 확률 (조합 수 기준)
P_RANK = {1: 1 / COMBOS, 2: 6 / COMBOS, 3: 228 / COMBOS, 4: 11_115 / COMBOS, 5: 182_780 / COMBOS}

tab_gen, tab_life, tab_fate, tab_stats, tab_history, tab_proof = st.tabs(
    ["🎰 번호 뽑기", "💸 인생 시뮬", "🔮 운명의 번호", "📊 역대 통계", "📜 역대 번호", "⚖️ 랜덤 증명"]
)

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

    if st.button("번호 뽑기 🎲", type="primary", width="stretch"):
        _, fn = MODES[mode]
        for i in range(n_games):
            picks = fn(stats)
            c1, c2 = st.columns([1, 9])
            c1.markdown(f"<div style='line-height:42px;color:{MUTED}'>{chr(65 + i)}게임</div>", unsafe_allow_html=True)
            c2.markdown(balls_html(picks), unsafe_allow_html=True)
        st.caption("※ 어디까지나 재미! 모든 조합의 당첨 확률은 똑같이 1/8,145,060")

# ── 탭 2: 인생 시뮬레이터 ────────────────────────────────────
with tab_life:
    st.subheader("이 번호로 평생 샀다면? 💸")

    def _auto_pick():
        st.session_state.life_picks = sorted(random.sample(range(1, 46), 6))

    st.button("🎲 번호 자동 선택", on_click=_auto_pick)
    picks = st.multiselect("번호 6개 고르기", list(range(1, 46)), max_selections=6, key="life_picks")

    if len(picks) == 6:
        st.markdown(balls_html(sorted(picks)), unsafe_allow_html=True)

        # ── 과거 성적표: 역대 전 회차에 이 번호로 응모했다면 ──
        picks_arr = np.array(picks)
        mc = np.isin(nums, picks_arr).sum(axis=1)
        bonus_hit = np.isin(df["bonus"].to_numpy(), picks_arr)
        first_prize = df["first_prize"].fillna(2_000_000_000).to_numpy()

        r = {
            1: mc == 6,
            2: (mc == 5) & bonus_hit,
            3: (mc == 5) & ~bonus_hit,
            4: mc == 4,
            5: mc == 3,
        }
        winnings = (
            r[1] * first_prize + r[2] * PRIZE[2] + r[3] * PRIZE[3]
            + r[4] * PRIZE[4] + r[5] * PRIZE[5]
        )
        spend = TICKET * len(nums)
        total_win = int(winnings.sum())

        st.markdown(f"#### 📋 과거 성적표 — 1회부터 {int(latest['draw_no'])}회까지 전부 샀다면")
        m1, m2, m3 = st.columns(3)
        m1.metric("총 지출", f"{spend / 1e4:,.0f}만원")
        m2.metric("총 당첨금", f"{total_win / 1e4:,.0f}만원")
        m3.metric("수익률", f"{(total_win - spend) / spend * 100:+.1f}%")

        rank_names = {1: "🥇 1등", 2: "🥈 2등", 3: "🥉 3등", 4: "4등", 5: "5등"}
        hits = {k: int(v.sum()) for k, v in r.items()}
        st.markdown(" · ".join(f"{rank_names[k]} **{hits[k]}번**" for k in range(1, 6)))

        if hits[1] > 0:
            st.balloons()
            st.success("아니 형님 이 번호 뭐야?! 역대 1등 번호랑 겹쳤어!!")
        elif hits[2] + hits[3] > 0:
            st.snow()

        profit = np.cumsum(winnings) - TICKET * np.arange(1, len(nums) + 1)
        fig = go.Figure(go.Scatter(
            x=df["draw_no"], y=profit, line=dict(color=BLUE, width=2),
            hovertemplate="%{x}회차 · 누적 %{y:,.0f}원<extra></extra>",
        ))
        fig.add_hline(y=0, line_color=MUTED, line_width=1)
        fig.update_yaxes(title="누적 손익 (원)")
        fig.update_xaxes(title="회차")
        st.plotly_chart(base_layout(fig, height=300), width="stretch")

        # ── 미래 시뮬: 1등 나올 때까지 ──
        st.markdown("#### 🔮 미래 시뮬 — 1등 나올 때까지 계속 산다면")
        weekly = st.slider("매주 몇 게임씩?", 1, 20, 5)
        st.caption(f"주당 {weekly * TICKET:,}원 · 1등 확률은 게임당 1/{COMBOS:,}")

        if st.button("1등 나올 때까지 산다!! 💸", type="primary", width="stretch"):
            rng = np.random.default_rng()
            games = int(rng.geometric(P_RANK[1]))          # 1등까지 걸리는 게임 수
            years = games / weekly / 52
            lower_hits = {k: int(rng.binomial(games, P_RANK[k])) for k in range(2, 6)}
            sim_spend = games * TICKET
            sim_win = 2_000_000_000 + sum(lower_hits[k] * PRIZE[k] for k in range(2, 6))

            with st.status("💸 돈이 녹는 중...", expanded=True) as status:
                for frac in (0.05, 0.2, 0.45, 0.7, 0.9):
                    y = years * frac
                    spent_so_far = sim_spend * frac
                    st.write(f"🗓️ {y:,.0f}년째 — 누적 지출 {spent_so_far / 1e8:,.1f}억, 아직 1등 없음...")
                    time.sleep(0.4)
                status.update(label=f"🎉 드디어 1등!! {years:,.0f}년 걸렸습니다", state="complete")
            st.balloons()

            c1, c2, c3 = st.columns(3)
            c1.metric("걸린 시간", f"{years:,.0f}년")
            c2.metric("총 지출", f"{sim_spend / 1e8:,.1f}억원")
            c3.metric("최종 손익", f"{(sim_win - sim_spend) / 1e8:+,.1f}억원")
            st.markdown(
                f"그동안 2등 {lower_hits[2]}번 · 3등 {lower_hits[3]}번 · "
                f"4등 {lower_hits[4]:,}번 · 5등 {lower_hits[5]:,}번 맞았어"
            )
            joseon = years / 500
            st.caption(
                f"참고로 {years:,.0f}년은 조선왕조({500}년)를 약 {joseon:,.0f}번 반복하는 시간 ㅋㅋ "
                "그래도 매주 사는 그 재미가 어디 가나."
            )
    else:
        st.info("번호 6개를 고르거나 🎲 자동 선택을 눌러줘")

# ── 탭 3: 운명의 번호 ────────────────────────────────────────
with tab_fate:
    st.subheader("오늘의 운명 번호 🔮")
    st.caption("이름 + 생년월일 + 오늘 꾼 꿈으로 정해지는 운명의 조합. 같은 입력이면 같은 번호가 나와 — 운명이니까.")

    name = st.text_input("이름", placeholder="홍길동")
    birth = st.date_input("생년월일", value=date(1990, 1, 1), min_value=date(1930, 1, 1), max_value=date.today())
    dream = st.text_input("오늘 꾼 꿈 (선택)", placeholder="돼지가 우리집 문을 부수고 들어옴")

    if st.button("운명 확인 ✨", type="primary", width="stretch"):
        if not name.strip():
            st.warning("이름은 넣어줘야 운명을 계산하지 ㅋㅋ")
        else:
            seed_src = f"{name.strip()}|{birth}|{dream.strip()}|{date.today()}"
            digest = hashlib.sha256(seed_src.encode("utf-8")).digest()
            fate_rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
            fate_nums = sorted((fate_rng.choice(45, size=6, replace=False) + 1).tolist())

            fortunes = [
                "오늘 서쪽에서 귀인이 나타난다. 귀인이 로또는 안 사줌.",
                "재물운이 상승 중. 다만 8,145,060분의 1만큼 상승.",
                "꿈자리가 심상치 않다. 특히 돼지꿈이면 국룰이지.",
                "조상님이 밀어주는 조합. 책임은 안 지신다고 하심.",
                "이 번호의 기운이 맑고 균형이 좋다. 통계적으로는 아무 의미 없다.",
                "오늘은 사는 것 자체가 행운. 당첨은 별개의 문제.",
            ]
            st.markdown(balls_html(fate_nums, size=44), unsafe_allow_html=True)
            st.info(f"🧙 {fortunes[digest[8] % len(fortunes)]}")
            st.caption(
                "※ 과학적 근거 0%임을 본 프로젝트가 직접 증명했습니다 (⚖️ 랜덤 증명 탭 참고). "
                "내일이 되면 운명도 바뀝니다."
            )

# ── 탭 4: 역대 통계 ──────────────────────────────────────────
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
    st.plotly_chart(base_layout(fig), width="stretch")

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
    st.plotly_chart(base_layout(fig), width="stretch")

    st.subheader("번호 합계 분포")
    sums = nums.sum(axis=1)
    fig = go.Figure(go.Histogram(
        x=sums, xbins=dict(start=20, end=260, size=10), marker_color=BLUE,
        marker_line=dict(color="rgba(0,0,0,0)", width=1),
        hovertemplate="합계 %{x} · %{y}회차<extra></extra>",
    ))
    fig.add_vline(x=float(sums.mean()), line_dash="dash", line_color=INK_2ND, line_width=1,
                  annotation_text=f"평균 {sums.mean():.0f}", annotation_font_color=INK_2ND)
    st.plotly_chart(base_layout(fig, height=320), width="stretch")

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
    st.plotly_chart(base_layout(fig, height=320), width="stretch")

# ── 탭 5: 역대 번호 ──────────────────────────────────────────
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
        width="stretch", hide_index=True, height=420,
    )

# ── 탭 6: 랜덤 증명 ──────────────────────────────────────────
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
