"""동행복권 로또 당첨번호 수집기.

1순위: 동행복권 공식 JSON API (회차별 조회)
2순위: smok95 GitHub Pages 미러 (공식 사이트가 간소화 페이지 모드일 때)

이미 수집한 회차는 건너뛰고 새 회차만 추가한다 (증분 수집).
결과는 data/lotto.csv 에 저장.
"""

import csv
import time
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent / "data"
CSV_PATH = DATA_DIR / "lotto.csv"

OFFICIAL_URL = "https://www.dhlottery.co.kr/common.do"
MIRROR_URL = "https://smok95.github.io/lotto/results/all.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}

FIELDS = [
    "draw_no", "date",
    "n1", "n2", "n3", "n4", "n5", "n6", "bonus",
    "first_prize", "first_winners", "total_sales",
]


def load_existing() -> dict[int, dict]:
    """기존 CSV를 읽어 회차 번호 -> 행 딕셔너리로 반환."""
    if not CSV_PATH.exists():
        return {}
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        return {int(row["draw_no"]): row for row in csv.DictReader(f)}


def save(rows: dict[int, dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for no in sorted(rows):
            writer.writerow(rows[no])


def fetch_official(drw_no: int, session: requests.Session) -> dict | None:
    """공식 API에서 한 회차 조회. 간소화 페이지(HTML)면 None."""
    r = session.get(
        OFFICIAL_URL,
        params={"method": "getLottoNumber", "drwNo": drw_no},
        headers=HEADERS,
        timeout=10,
    )
    if "json" not in r.headers.get("Content-Type", ""):
        return None  # 간소화 페이지 모드
    data = r.json()
    if data.get("returnValue") != "success":
        return None  # 아직 추첨 안 된 회차
    return {
        "draw_no": data["drwNo"],
        "date": data["drwNoDate"],
        **{f"n{i}": data[f"drwtNo{i}"] for i in range(1, 7)},
        "bonus": data["bnusNo"],
        "first_prize": data["firstWinamnt"],
        "first_winners": data["firstPrzwnerCo"],
        "total_sales": data["totSellamnt"],
    }


def fetch_mirror() -> list[dict]:
    """미러에서 전체 회차 한 번에 조회."""
    r = requests.get(MIRROR_URL, timeout=30)
    r.raise_for_status()
    rows = []
    for d in r.json():
        first = d["divisions"][0] if d["divisions"] else {}
        nums = sorted(d["numbers"])
        rows.append({
            "draw_no": d["draw_no"],
            "date": d["date"][:10],
            **{f"n{i}": nums[i - 1] for i in range(1, 7)},
            "bonus": d["bonus_no"],
            "first_prize": first.get("prize", ""),
            "first_winners": first.get("winners", ""),
            "total_sales": d.get("total_sales_amount", ""),
        })
    return rows


def main() -> None:
    rows = load_existing()
    start = max(rows) + 1 if rows else 1
    print(f"기존 수집: {len(rows)}회차 (다음 수집 대상: {start}회)")

    session = requests.Session()

    # 공식 API가 살아있는지 1회차로 확인
    official_ok = fetch_official(1, session) is not None

    if official_ok:
        print("공식 API 사용")
        drw_no = start
        while True:
            row = fetch_official(drw_no, session)
            if row is None:
                break
            rows[drw_no] = row
            if drw_no % 100 == 0:
                print(f"  {drw_no}회차까지 수집...")
            drw_no += 1
            time.sleep(0.2)  # 서버 예의
    else:
        print("공식 API 응답 없음(간소화 페이지) → 미러 사용")
        for row in fetch_mirror():
            if row["draw_no"] >= start:
                rows[row["draw_no"]] = row

    save(rows)
    latest = max(rows)
    print(f"완료: 총 {len(rows)}회차 저장 (최신 {latest}회, {rows[latest]['date']}) → {CSV_PATH}")


if __name__ == "__main__":
    main()
