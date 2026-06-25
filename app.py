import streamlit as st
import pandas as pd
import requests

# ====================================================
# 1. 페이지 기본 설정
# ====================================================
st.set_page_config(
    page_title="2026 월드컵 대한민국 32강 진출 예측기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2026 북중미 월드컵 본선 주요국 국문 매핑 (실제 참가국 기준 반영)
COUNTRY_MAP = {
    "South Korea": "대한민국", "Korea Republic": "대한민국", "Korea": "대한민국",
    "USA": "미국", "Mexico": "멕시코", "Canada": "캐나다",
    "Argentina": "아르헨티나", "France": "프랑스", "잉글랜드": "England",
    "Spain": "스페인", "Germany": "독일", "Japan": "일본",
    "Morocco": "모로코", "Uruguay": "우루과이", "Saudi Arabia": "사우디"
}

# ----------------------------------------------------
# 조별 리그 순위 정렬 및 실시간 3위 추출 함수
# ----------------------------------------------------
def process_groups_and_third_places(full_df):
    if full_df.empty:
        return full_df, pd.DataFrame()
        
    ordered_groups = []
    third_places = []
    
    groups = full_df["조"].unique()
    for g in groups:
        group_df = full_df[full_df["조"] == g].copy()
        group_df = group_df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
        group_df["조내순위"] = group_df.index + 1
        ordered_groups.append(group_df)
        
        if len(group_df) >= 3:
            third_team = group_df.iloc[2].copy()
            third_places.append(third_team)
            
    return pd.concat(ordered_groups).reset_index(drop=True), pd.DataFrame(third_places).reset_index(drop=True)


def calculate_wildcard_rank(df):
    if df.empty:
        return df
    df = df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
    df["순위"] = df.index + 1
    df["진출"] = df["순위"] <= 8
    return df[["순위", "조", "국가", "승점", "골득실", "득점", "남은경기", "진출"]]


# ----------------------------------------------------
# [실시간] API 데이터 로드 함수 (2026 실제 데이터 타겟팅)
# ----------------------------------------------------
@st.cache_data(ttl=60)
def fetch_realtime_standings():
    # 2026년 현재 대회 상황을 모사한 현실적인 기본 베이스 데이터
    mock_all_teams = [
        # 대한민국이 속한 조 시뮬레이션
        {"국가": "프랑스", "승점": 6, "골득실": 4, "득점": 5, "남은경기": 1, "조": "A조"},
        {"국가": "우루과이", "승점": 4, "골득실": 1, "득점": 3, "남은경기": 1, "조": "A조"},
        {"국가": "대한민국", "승점": 3, "골득실": 0, "득점": 2, "남은경기": 1, "조": "A조"}, 
        {"국가": "캐나다", "승점": 0, "골득실": -5, "득점": 0, "남은경기": 1, "조": "A조"},
        
        # B조 
        {"국가": "아르헨티나", "승점": 7, "골득실": 5, "득점": 6, "남은경기": 0, "조": "B조"},
        {"국가": "독일", "승점": 6, "골득실": 2, "득점": 4, "남은경기": 0, "조": "B조"},
        {"국가": "일본", "승점": 3, "골득실": -1, "득점": 2, "남은경기": 1, "조": "B조"},
        {"국가": "모로코", "승점": 1, "골득실": -6, "득점": 1, "남은경기": 1, "조": "B조"},
        
        # C조
        {"국가": "스페인", "승점": 4, "골득실": 2, "득점": 3, "남은경기": 1, "조": "C조"},
        {"국가": "미국", "승점": 3, "골득실": 0, "득점": 2, "남은경기": 1, "조": "C조"},
        {"국가": "사우디", "승점": 2, "골득실": -1, "득점": 1, "남은경기": 1, "조": "C조"},
        {"국가": "멕시코", "승점": 1, "골득실": -1, "득점": 1, "남은경기": 1, "조": "C조"},
    ]
    
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {"x-apisports-key": API_KEY}
        # 2026 월드컵 본선 전용 API Endpoint 호출
        url = "https://v3.football.api-sports.io/standings?league=1&season=2026"
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if "response" in data and data["response"]:
            standings_list = data["response"][0].get("league", {}).get("standings", [])
            all_teams_data = []
            
            for group_idx, group in enumerate(standings_list):
                alphabet = chr(65 + group_idx)
                if isinstance(group, list):
                    for team_info in group:
                        team_obj = team_info.get("team", {})
                        eng_name = team_obj.get("name", "Unknown")
                        kor_name = COUNTRY_MAP.get(eng_name, eng_name)
                        
                        played = team_info.get("all", {}).get("played", 2)
                        remaining_games = max(0, 3 - played)
                        
                        all_teams_data.append({
                            "국가": kor_name,
                            "승점": team_info.get("points", 0),
                            "골득실": team_info.get("goalsDiff", 0),
                            "득점": team_info.get("all", {}).get("goals", {}).get("for", 0),
                            "남은경기": remaining_games,
                            "조": f"{alphabet}조"
                        })
            
            full_df = pd.DataFrame(all_teams_data)
            if not full_df.empty:
                return full_df
        
        return pd.DataFrame(mock_all_teams)
    except Exception as e:
        return pd.DataFrame(mock_all_teams)


# ====================================================
# 2. 데이터 연산 프로세스
# ====================================================
all_teams_raw = fetch_realtime_standings()
all_groups_ordered, third_places_raw = process_groups_and_third_places(all_teams_raw)
wildcard_ranking = calculate_wildcard_rank(third_places_raw)

korea_df = wildcard_ranking[wildcard_ranking["국가"].str.contains("대한민국|Korea", case=False)]
has_korea_data = not korea_df.empty

# ====================================================
# 3. 메인 대시보드 화면 UI
# ====================================================
st.title("⚽ 2026 북중미 월드컵 실시간 32강 와일드카드 계산기")

if has_korea_data:
    korea = korea_df.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("실시간 와일드카드 순위", f"조 3위 중 {int(korea['순위'])}위")
    col2.metric("32강 진출 가능성", "✅ 진출 안정권(상위 8개팀)" if korea["순위"] <= 8 else "❌ 탈락 위험군")
    col3.metric("대한민국 잔여 경기", f"{int(korea['남은경기'])} 경기")
st.divider()

# 중간 섹션: 와일드카드 순위표
st.subheader("📊 2026 월드컵 각 조 3위 간 실시간 와일드카드 순위")
st.dataframe(wildcard_ranking, use_container_width=True)

st.divider()

# 하단 섹션: 2026년 실시간 조별 상황판
st.subheader("🔍 2026 월드컵 실시간 조별 순위 현황")
st.caption("※ API 무료 플랜 제한으로 인해 서버가 비어있을 때는 2026년 현재 타겟 시뮬레이션 데이터가 활성화됩니다.")

group_cols = st.columns(3)
unique_groups = all_groups_ordered["조"].unique()

# 2026년 실제 조별 일정 시나리오 매핑
real_2026_matches = {
    "A조": ["🇰🇷 대한민국 vs 🇺🇾 우루과이 (조별리그 최종전)", "🇫🇷 프랑스 vs 🇨🇦 캐나다"],
    "B조": ["🇯🇵 일본 vs 🇲🇦 모로코 (최종전)", "※ 아르헨티나/독일 조별리그 경기 종료"],
    "C조":
}

for idx, g_name in enumerate(unique_groups):
    with group_cols[idx % 3]:
        st.markdown(f"### 📍 {g_name}")
        g_df = all_groups_ordered[all_groups_ordered["조"] == g_name][["조내순위", "국가", "승점", "골득실", "남은경기"]]
        st.dataframe(g_df, use_container_width=True, hide_index=True)
        
        st.markdown("**📅 조별 잔여 매치업:**")
        matches = real_2026_matches.get(g_name, ["잔여 경기 로드 중..."])
        for m in matches:
            st.write(f"• {m}")
        st.write("")
