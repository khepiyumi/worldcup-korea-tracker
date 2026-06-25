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

# API 영문 국가명을 국문으로 자동 변환하기 위한 매핑 (존재하는 데이터만 변환)
COUNTRY_MAP = {
    "South Korea": "대한민국", "Korea Republic": "대한민국", "Korea": "대한민국",
    "Mexico": "멕시코", "Czech Republic": "체코", "Czechia": "체코"
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
# [순수 실시간] API 데이터 로드 함수 (잘못된 백업 데이터 전면 삭제)
# ----------------------------------------------------
@st.cache_data(ttl=60)
def fetch_realtime_standings():
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
                # API 내부에 조 이름(예: 'Group A')이 있으면 사용, 없으면 알파벳 부여
                group_name = group[0].get("group", f"{chr(65 + group_idx)}조") if isinstance(group, list) and group else f"{chr(65 + group_idx)}조"
                
                # 대한민국이 포함된 조는 직관적으로 표시
                is_korea_group = any(t.get("team", {}).get("name") in ["South Korea", "Korea Republic"] for t in group)
                if is_korea_group:
                    group_name = "대한민국 속한 조"
                
                if isinstance(group, list):
                    for team_info in group:
                        team_obj = team_info.get("team", {})
                        eng_name = team_obj.get("name", "Unknown")
                        kor_name = COUNTRY_MAP.get(eng_name, eng_name) # 매핑 있으면 국문, 없으면 영문 그대로 유지
                        
                        played = team_info.get("all", {}).get("played", 2)
                        remaining_games = max(0, 3 - played)
                        
                        all_teams_data.append({
                            "국가": kor_name,
                            "승점": team_info.get("points", 0),
                            "골득실": team_info.get("goalsDiff", 0),
                            "득점": team_info.get("all", {}).get("goals", {}).get("for", 0),
                            "남은경기": remaining_games,
                            "조": group_name
                        })
            
            full_df = pd.DataFrame(all_teams_data)
            if not full_df.empty:
                return full_df
                
        return pd.DataFrame() # 데이터가 비어있으면 빈 값 반환
    except Exception as e:
        return pd.DataFrame()


# ====================================================
# 2. 데이터 연산 프로세스
# ====================================================
all_teams_raw = fetch_realtime_standings()

# 데이터가 정상적으로 수집되었을 때만 화면 렌더링 진행
if not all_teams_raw.empty:
    all_groups_ordered, third_places_raw = process_groups_and_third_places(all_teams_raw)
    wildcard_ranking = calculate_wildcard_rank(third_places_raw)
    korea_df = wildcard_ranking[wildcard_ranking["국가"].str.contains("대한민국|Korea", case=False)]
    has_korea_data = not korea_df.empty
else:
    has_korea_data = False

# ====================================================
# 3. 메인 대시보드 화면 UI
# ====================================================
st.title("⚽ 2026 북중미 월드컵 실시간 32강 와일드카드 계산기")

if not all_teams_raw.empty:
    if has_korea_data:
        korea = korea_df.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("실시간 와일드카드 순위", f"조 3위 중 {int(korea['순위'])}위")
        col2.metric("32강 진출 자격", "✅ 진출 안정권" if korea["순위"] <= 8 else "❌ 탈락 위험군")
        col3.metric("대한민국 잔여 경기", f"{int(korea['남은경기'])} 경기")
    else:
        st.success("🎉 대한민국이 현재 조 2위 이상에 위치해 있어 와일드카드 비교 대상이 아닌 '자력 진출 권역'입니다!")
        
    st.divider()

    # 와일드카드 순위표
    st.subheader("📊 각 조 3위 간 실시간 와일드카드 순위")
    st.dataframe(wildcard_ranking, use_container_width=True)

    st.divider()

    # 조별 실시간 상황판 (100% API 기반 자동 노출)
    st.subheader("🔍 2026 월드컵 실시간 조별 순위 현황")
    
    unique_groups = all_groups_ordered["조"].unique()
    group_cols = st.columns(3)
    
    for idx, g_name in enumerate(unique_groups):
        with group_cols[idx % 3]:
            st.markdown(f"### 📍 {g_name}")
            g_df = all_groups_ordered[all_groups_ordered["조"] == g_name][["조내순위", "국가", "승점", "골득실", "남은경기"]]
            st.dataframe(g_df, use_container_width=True, hide_index=True)
else:
    # API 호출이 제한되었을 때 노출할 깔끔한 예외 메시지
    st.warning("⚠️ 현재 API 서비스(Free 플랜)의 제한으로 인해 월드컵 실시간 데이터를 불러올 수 없습니다.")
    st.info("💡 요금제 제한이 풀리거나 API가 활성화되면 자동으로 동기화되어 실시간 [대한민국-멕시코-체코] 조 편성 순위가 자동으로 렌더링됩니다.")
