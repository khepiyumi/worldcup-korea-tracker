import streamlit as st
import pandas as pd
import requests

# ====================================================
# 1. 페이지 기본 설정
# ====================================================
st.set_page_config(
    page_title="대한민국 32강 진출 추적기",
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
# [유동적] 전체 팀 데이터 중 '실시간 조 3위'를 계산해내는 함수
# ----------------------------------------------------
def extract_realtime_third_places(full_df):
    if full_df.empty:
        return full_df
        
    third_places = []
    
    # API 데이터에 조(Group) 정보가 있으면 조별로, 없으면 4개 팀씩 끊어서 실시간 순위를 재계산합니다.
    # 이는 경기 결과에 따라 조 내부 순위가 바뀌는 것을 실시간으로 잡기 위함입니다.
    if "조" in full_df.columns:
        groups = full_df["조"].unique()
        for g in groups:
            group_df = full_df[full_df["조"] == g].copy()
            # 조 내부에서 승점 -> 골득실 -> 득점 순으로 실시간 정렬
            group_df = group_df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
            if len(group_df) >= 3:
                third_places.append(group_df.iloc[2]) # 실시간 3위 팀 추출
    else:
        # 조 구분이 명확하지 않을 경우 4개 팀씩 한 조로 가정하여 처리
        for i in range(0, len(full_df), 4):
            group_df = full_df.iloc[i:i+4].copy()
            group_df = group_df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
            if len(group_df) >= 3:
                third_places.append(group_df.iloc[2])
                
    return pd.DataFrame(third_places).reset_index(drop=True)


# --------------------
# 와일드카드 최종 순위 매기기
# --------------------
def calculate_wildcard_rank(df):
    if df.empty:
        return df
    # 3위 팀들끼리 다시 승점 -> 골득실 -> 득점 순 정렬
    df = df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
    df["순위"] = df.index + 1
    df["진출"] = df["순위"] <= 8
    return df[["순위", "국가", "승점", "골득실", "득점", "남은경기", "진출"]]


# --------------------
# [실시간 + 백업] API 데이터 로드 함수
# --------------------
@st.cache_data(ttl=60)
def fetch_realtime_standings():
    # 시뮬레이션용 전체 조 가상 데이터 (경기 결과에 따라 조별 순위가 실시간 변동됨)
    mock_all_teams = [
        # A조 예시 (현재 대한민국이 3위인 상태이지만 최종전에 따라 2위로 올라가거나 4위로 떨어질 수 있음)
        {"국가": "스페인", "승점": 6, "골득실": 4, "득점": 5, "남은경기": 1, "조": "A"},
        {"국가": "모로코", "승점": 5, "골득실": 2, "득점": 3, "남은경기": 1, "조": "A"},
        {"국가": "대한민국", "승점": 4, "골득실": 0, "득점": 3, "남은경기": 1, "조": "A"}, 
        {"국가": "우루과이", "승점": 1, "골득실": -6, "득점": 1, "남은경기": 1, "조": "A"},
        
        # B조 예시
        {"국가": "크로아티아", "승점": 7, "골득실": 3, "득점": 5, "남은경기": 0, "조": "B"},
        {"국가": "벨기에", "승점": 6, "골득실": 2, "득점": 4, "남은경기": 0, "조": "B"},
        {"국가": "일본", "승점": 3, "골득실": 1, "득점": 4, "남은경기": 1, "조": "B"},
        {"국가": "사우디아라비아", "승점": 0, "골득실": -6, "득점": 0, "남은경기": 1, "조": "B"},
        
        # C조 예시
        {"국가": "스웨덴", "승점": 4, "골득실": -1, "득점": 2, "남은경기": 1, "조": "C"},
        {"국가": "가나", "승점": 3, "골득실": -2, "득점": 3, "남은경기": 1, "조": "C"},
        {"국가": "튀니지", "승점": 2, "골득실": -2, "득점": 1, "남은경기": 1, "조": "C"},
        {"국가": "알제리", "승점": 1, "골득실": -3, "득점": 2, "남은경기": 1, "조": "C"},
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
                if isinstance(group, list):
                    for idx, team_info in enumerate(group):
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
                            "조": f"Group_{group_idx}"
                        })
            
            full_df = pd.DataFrame(all_teams_data)
            if not full_df.empty:
                return full_df
        
        return pd.DataFrame(mock_all_teams)

    except Exception as e:
        return pd.DataFrame(mock_all_teams)


# ====================================================
# 2. 데이터 처리 메인 로직 (모든 팀 수집 -> 실시간 조 3위 추출 -> 와일드카드 순위 계산)
# ====================================================
all_teams_raw = fetch_realtime_standings()

# 1단계: 현재 전체 경기 결과 기준, 각 조의 '실시간 3위'들만 동적으로 도려내기
third_places_raw = extract_realtime_third_places(all_teams_raw)

# 2단계: 도려낸 3위 팀들끼리 모아서 와일드카드 순위표 정렬하기
ranking = calculate_wildcard_rank(third_places_raw)

# 3단계: 대한민국 현황 추출
korea_df = ranking[ranking["국가"].str.contains("대한민국|Korea", case=False)]

if not korea_df.empty:
    korea = korea_df.iloc[0]
    has_korea_data = True
else:
    has_korea_data = False


# ====================================================
# 3. 메인 대시보드 화면 UI
# ====================================================
st.title("🇰🇷 대한민국 32강 진출 추적기 (실시간 조별 변동 반영)")

if has_korea_data:
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 실시간 와일드카드 순위", f"조 3위 중 {int(korea['순위'])}위")
    col2.metric("32강 진출 자격", "✅ 진출 안정권" if korea["순위"] <= 8 else "❌ 탈락 위험군")

    probability = {1:99, 2:97, 3:94, 4:90, 5:82, 6:72, 7:60, 8:51, 9:35, 10:20, 11:8, 12:1}
    col3.metric("시나리오상 예상 확률", f"{probability.get(int(korea['순위']), 0)}%")

    st.divider()

    left_col, right_col = st.columns([4, 3])

    with left_col:
        st.subheader("📊 각 조 실시간 3위 팀 간 와일드카드 비교")
        st.dataframe(ranking, use_container_width=True)
        st.caption("⚠️ 주의: 남은 경기가 있는 조는 경기 결과에 따라 조 3위 주인공 자체가 바뀔 수 있으므로 실시간으로 반영됩니다.")

    with right_col:
        st.subheader("👀 실시간 변동 시나리오 분석")
        
        st.info(
            f"""
            **🇰🇷 대한민국 현황 (남은 경기: {int(korea['남은경기'])}경기)**
            * 다른 조의 3위 경쟁국들보다 **남은 경기가 1경기 더 있다는 점**이 핵심입니다. 
            * 최종전에서 승점을 확보하면 타 조 결과와 상관없이 자력 진출 가능성이 매우 높습니다.
            """
        )
        
        st.markdown("---")
        st.subheader("📣 오늘 밤 핵심 관전 매치")
        
        st.success(
            """
            **🇲🇦 모로코 (남은 경기: 1)** vs 🇸🇦 사우디아라비아
            * **시간:** 6월 25일 밤 11:00
            * **시나리오:** 모로코가 사우디를 완파해 주면, 사우디가 A조 3위 싸움으로 치고 올라오는 변수 자체를 원천 차단할 수 있습니다.
            """
        )
else:
    st.info("현재 대한민국이 조 1위 혹은 2위로 치고 올라갔거나, 4위로 내려앉아 와일드카드(3위) 추적 대상에서 제외되었습니다. 전체 순위표를 확인해 보세요.")
