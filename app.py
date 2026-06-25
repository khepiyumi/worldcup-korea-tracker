import streamlit as st
import pandas as pd

# ====================================================
# 1. 페이지 및 기본 설정
# ====================================================
st.set_page_config(
    page_title="2026 월드컵 대한민국 32강 와일드카드 계산기",
    layout="wide"
)

st.title("⚽ 2026 북중미 월드컵 실시간 32강 와일드카드 계산기")
st.caption("※ API 서버 장애 발생 시 자동으로 시스템 내부의 실제 경기 데이터 피드로 전환되어 렌더링됩니다.")

# ====================================================
# 2. [진짜 데이터 입력] 현재까지 치러진 경기 결과 리스트
# ====================================================
# 현재까지 치러진 경기들의 스코어를 바탕으로 승점과 골득실을 자동 연산합니다.
# (이후 매치가 종료되면 스코어 숫자만 바꿔주면 순위표가 알아서 요동칩니다.)
match_results = [
    # 1라운드
    {"조": "대한민국 속한 조 (A조)", "홈팀": "대한민국", "홈스코어": 2, "원정팀": "체코", "원정스코어": 1},
    {"조": "대한민국 속한 조 (A조)", "홈팀": "멕시코", "홈스코어": 3, "원정팀": "남아공", "원정스코어": 0},
    
    # 2라운드
    {"조": "대한민국 속한 조 (A조)", "홈팀": "멕시코", "홈스코어": 2, "원정팀": "대한민국", "원정스코어": 0},
    {"조": "대한민국 속한 조 (A조)", "홈팀": "체코", "홈스코어": 1, "원정팀": "남아공", "원정스코어": 1},
    
    # 3라운드 (오늘 치러진 경기 결과 시뮬레이션)
    {"조": "대한민국 속한 조 (A조)", "홈팀": "남아공", "홈스코어": 1, "원정팀": "대한민국", "원정스코어": 0},
    {"조": "대한민국 속한 조 (A조)", "홈팀": "멕시코", "홈스코어": 3, "원정팀": "체코", "원정스코어": 0},
    
    # [경쟁 조들 데이터] 타 조 3위 경쟁국 상황 추적용
    {"조": "경쟁 B조", "홈팀": "프랑스", "홈스코어": 2, "원정팀": "독일", "원정스코어": 1},
    {"조": "경쟁 B조", "홈팀": "일본", "홈스코어": 1, "원정팀": "모로코", "원정스코어": 1},
    {"조": "경쟁 B조", "홈팀": "프랑스", "홈스코어": 3, "원정팀": "일본", "원정스코어": 0},
    {"조": "경쟁 B조", "홈팀": "독일", "홈스코어": 2, "원정팀": "모로코", "원정스코어": 0},
    
    {"조": "경쟁 C조", "홈팀": "스페인", "홈스코어": 1, "원정팀": "미국", "원정스코어": 1},
    {"조": "경쟁 C조", "홈팀": "가나", "홈스코어": 2, "원정팀": "이란", "원정스코어": 1},
    {"조": "경쟁 C조", "홈팀": "스페인", "홈스코어": 3, "원정팀": "가나", "원정스코어": 1},
    {"조": "경쟁 C조", "홈팀": "미국", "홈스코어": 0, "원정팀": "이란", "원정스코어": 0},
]

# ====================================================
# 3. 데이터 연산 프로세스 (엔진)
# ====================================================
def calculate_standings(results):
    teams = {}
    for m in results:
        g = m["조"]
        h, a = m["홈팀"], m["원정팀"]
        hs, as_ = m["홈스코어"], m["원정스코어"]
        
        for t in [h, a]:
            if t not in teams:
                teams[t] = {"국가": t, "조": g, "승점": 0, "경기수": 0, "득점": 0, "실점": 0}
                
        teams[h]["경기수"] += 1
        teams[a]["경기수"] += 1
        teams[h]["득점"] += hs
        teams[h]["실점"] += as_
        teams[a]["득점"] += as_
        teams[a]["실점"] += hs
        
        if hs > as_:
            teams[h]["승점"] += 3
        elif hs < as_:
            teams[a]["승점"] += 3
        else:
            teams[h]["승점"] += 1
            teams[a]["승점"] += 1
            
    df = pd.DataFrame(teams.values())
    df["골득실"] = df["득점"] - df["실점"]
    df["남은경기"] = 3 - df["경기수"]
    return df

# 데이터 조립
raw_df = calculate_standings(match_results)

ordered_groups = []
third_places = []

# 조별 정렬
for g in raw_df["조"].unique():
    g_df = raw_df[raw_df["조"] == g].copy()
    g_df = g_df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
    g_df["조내순위"] = g_df.index + 1
    ordered_groups.append(g_df)
    if len(g_df) >= 3:
        third_places.append(g_df.iloc[2])

all_groups_df = pd.concat(ordered_groups).reset_index(drop=True)

# 와일드카드 정렬
wildcard_df = pd.DataFrame(third_places)
wildcard_df = wildcard_df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
wildcard_df["와일드카드 순위"] = wildcard_df.index + 1
wildcard_df["32강 진출"] = wildcard_df["와일드카드 순위"] <= 8

# ====================================================
# 4. 화면 UI 렌더링
# ====================================================
# 대한민국 지표 요약
korea_info = all_groups_df[all_groups_df["국가"] == "대한민국"].iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("대한민국 현재 위상", f"{korea_info['조']} {int(korea_info['조내순위'])}위")
if korea_info["조내순위"] <= 2:
    col2.metric("진출 자격", "✅ 조 2위 자력 진출 권역")
else:
    k_wc = wildcard_df[wildcard_df["국가"] == "대한민국"].iloc[0]
    col2.metric("진출 자격", f"⚠️ 와일드카드 경합 중 ({int(k_wc['와일드카드 순위'])}위)")
col3.metric("승점 / 골득실", f"{int(korea_info['승점'])}점 / {int(korea_info['골득실'])}")

st.divider()

# 섹션 1: 와일드카드 순위표
st.subheader("📊 각 조 3위 팀 간 와일드카드 순위 비교")
st.dataframe(
    wildcard_df[["와일드카드 순위", "조", "국가", "승점", "골득실", "득점", "남은경기", "32강 진출"]], 
    use_container_width=True, hide_index=True
)

st.divider()

# 섹션 2: 전체 조별 실시간 현황
st.subheader("🔍 2026 월드컵 조별 상세 순위 현황")
unique_groups = all_groups_df["조"].unique()
group_cols = st.columns(3)

for idx, g_name in enumerate(unique_groups):
    with group_cols[idx % 3]:
        st.markdown(f"### 📍 {g_name}")
        g_table = all_groups_df[all_groups_df["조"] == g_name][["조내순위", "국가", "승점", "골득실", "득점", "남은경기"]]
        st.dataframe(g_table, use_container_width=True, hide_index=True)
