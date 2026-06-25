import streamlit as st
import pandas as pd
import requests

# ====================================================
# 1. 페이지 기본 설정
# ====================================================
st.set_page_config(
    page_title="대한민국 32강 진출 시나리오 계산기",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 국가명 영문 -> 국문 매핑
COUNTRY_MAP = {
    "South Korea": "대한민국", "Korea Republic": "대한민국", "Korea": "대한민국",
    "Morocco": "모로코", "Spain": "스페인", "Japan": "일본", 
    "Sweden": "스웨덴", "Croatia": "크로아티아", "Belgium": "벨기에",
    "Tunisia": "튀니지", "Ghana": "가나", "Algeria": "알제리",
    "Uruguay": "우루과이", "Saudi Arabia": "사우디아라비아", "Canada": "캐나다"
}

# ----------------------------------------------------
# 조별 리그 실시간 순위 정렬 및 3위 추출 함수
# ----------------------------------------------------
def process_groups_and_third_places(full_df):
    if full_df.empty:
        return full_df, pd.DataFrame()
        
    ordered_groups = []
    third_places = []
    
    groups = full_df["조"].unique()
    for g in groups:
        group_df = full_df[full_df["조"] == g].copy()
        # 승점 -> 골득실 -> 득점 순 실시간 조별 정렬
        group_df = group_df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
        group_df["조내순위"] = group_df.index + 1
        ordered_groups.append(group_df)
        
        if len(group_df) >= 3:
            # 실시간 조 3위 데이터 복사 및 저장
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


# --------------------
# [실시간 + 백업] API 데이터 로드 함수
# --------------------
@st.cache_data(ttl=60)
def fetch_realtime_standings():
    # 시뮬레이션용 월드컵 전체 조 데이터셋
    mock_all_teams = [
        # A조
        {"국가": "스페인", "승점": 6, "골득실": 4, "득점": 5, "남은경기": 1, "조": "A조"},
        {"국가": "모로코", "승점": 5, "골득실": 2, "득점": 3, "남은경기": 1, "조": "A조"},
        {"국가": "대한민국", "승점": 4, "골득실": 0, "득점": 3, "남은경기": 1, "조": "A조"}, 
        {"국가": "우루과이", "승점": 1, "골득실": -6, "득점": 1, "남은경기": 1, "조": "A조"},
        
        # B조
        {"국가": "크로아티아", "승점": 7, "골득실": 3, "득점": 5, "남은경기": 0, "조": "B조"},
        {"국가": "벨기에", "승점": 6, "골득실": 2, "득점": 4, "남은경기": 0, "조": "B조"},
        {"국가": "일본", "승점": 3, "골득실": 1, "득점": 4, "남은경기": 1, "조": "B조"},
        {"국가": "사우디아라비아", "승점": 0, "골득실": -6, "득점": 0, "남은경기": 1, "조": "B조"},
        
        # C조
        {"국가": "스웨덴", "승점": 4, "골득실": -1, "득점": 2, "남은경기": 1, "조": "C조"},
        {"국가": "가나", "승점": 3, "골득실": -2, "득점": 3, "남은경기": 1, "조": "C조"},
        {"국가": "튀니지", "승점": 2, "골득실": -2, "득점": 1, "남은경기": 1, "조": "C조"},
        {"국가": "알제리", "승점": 1, "골득실": -3, "득점": 2, "남은경기": 1, "조": "C조"},
    ]
    
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {"x-apisports-key": API_KEY}
        url = "https://v3.football.api-sports.io/standings?league=1&season=2026"
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if "response" in data and data["response"]:
            standings_list = data["response"][0].get("league", {}).get("standings", [])
            all_teams_data = []
            
            for group_idx, group in enumerate(standings_list):
                alphabet = chr(65 + group_idx) # Group 0 -> A조, 1 -> B조...
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

# 조별 순위 재정렬 및 실시간 3위 팀만 분리수거
all_groups_ordered, third_places_raw = process_groups_and_third_places(all_teams_raw)

# 와일드카드 최종 순위 생성
wildcard_ranking = calculate_wildcard_rank(third_places_raw)

# 대한민국 정보 확인
korea_df = wildcard_ranking[wildcard_ranking["국가"].str.contains("대한민국|Korea", case=False)]
has_korea_data = not korea_df.empty


# ====================================================
# 3. 메인 대시보드 화면 UI
# ====================================================
st.title("⚽ 2026 북중미 월드컵 실시간 진출 예측 매치센터")

# 상단 위젯 (현재 대한민국 스펙 요약)
if has_korea_data:
    korea = korea_df.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("실시간 와일드카드 순위", f"조 3위 중 {int(korea['순위'])}위")
    col2.metric("현재 자격", "✅ 32강 진출 안정권" if korea["순위"] <= 8 else "❌ 탈락 위험")
    col3.metric("대한민국 남은 경기", f"{int(korea['남은경기'])} 경기")
st.divider()

# 중간 섹션: 와일드카드 순위표
st.subheader("📊 실시간 각 조 3위 팀 간 와일드카드 순위")
st.dataframe(wildcard_ranking, use_container_width=True)

st.divider()

# 하단 섹션 (NEW!): 유저 요청 반영 - 전 조의 상황과 남은 경기 대진표
st.subheader("🔍 조별 실시간 현재 순위 및 잔여 대진표")
st.caption("여기서 1, 2위 팀의 승점과 남은 경기 상대를 보고 3위 싸움의 변수를 시뮬레이션할 수 있습니다.")

# 3개의 열로 쪼개서 조별 상황을 이쁘게 배치
group_cols = st.columns(3)
unique_groups = all_groups_ordered["조"].unique()

# 각 조의 잔여 경기 텍스트 매핑 (하드코딩 데이터 - 예측 돕기용)
remaining_matches_info = {
    "A조": ["🇰🇷 대한민국 vs 🇺🇾 우루과이 (6/27)", "🇲🇦 모로코 vs 🇪🇸 스페인 (6/27)"],
    "B조": ["🇯🇵 일본 vs 🇸🇦 사우디아라비아 (6/26)", "※ 크로아티아/벨기에 전경기 종료"],
    "C조": ["🇸🇪 스웨덴 vs 🇩🇿 알제리 (6/26)", "🇬🇭 가나 vs 🇹🇳 튀니지 (6/26)"]
}

for idx, g_name in enumerate(unique_groups):
    # col0, col1, col2 순서로 순환 배치
    with group_cols[idx % 3]:
        st.markdown(f"### 📍 {g_name}")
        
        # 해당 조의 1~4위 순위표 출력
        g_df = all_groups_ordered[all_groups_ordered["조"] == g_name][["조내순위", "국가", "승점", "골득실", "남은경기"]]
        st.dataframe(g_df, use_container_width=True, hide_index=True)
        
        # 해당 조의 남은 핵심 경기 리스트 노출
        st.markdown("**📅 남은 핵심 경기 일정:**")
        matches = remaining_matches_info.get(g_name, ["남은 경기 일정 데이터 업데이트 중"])
        for m in matches:
            st.write(f"• {m}")
        st.write("") # 간격 맞춤용 공백
