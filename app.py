import streamlit as st
import pandas as pd
import requests

# ====================================================
# 1. 페이지 기본 설정 (반드시 최상단에 위치해야 합니다)
# ====================================================
st.set_page_config(
    page_title="대한민국 32강 진출 추적기",
    layout="wide"
)

# 국가명 영문 -> 국문 매핑 딕셔너리
COUNTRY_MAP = {
    "South Korea": "대한민국",
    "Korea Republic": "대한민국",
    "Korea": "대한민국",
    "Bosnia": "보스니아",
    "Sweden": "스웨덴",
    "Algeria": "알제리",
    "Croatia": "크로아티아",
    "Scotland": "스코틀랜드",
    "Belgium": "벨기에",
    "Tunisia": "튀니지",
    "Spain": "스페인",
    "Morocco": "모로코",
    "Japan": "일본",
    "Ghana": "가나"
}

# --------------------
# 순위 계산 함수
# --------------------
def calculate_rank(df):
    if df.empty:
        return df
        
    # 승점 -> 골득실 -> 득점 순으로 내림차순 정렬
    df = df.sort_values(
        ["승점", "골득실", "득점"],
        ascending=False
    ).reset_index(drop=True)

    df["순위"] = df.index + 1
    df["진출"] = df["순위"] <= 8  # 와일드카드 상위 8개팀 진출 자격

    return df


# --------------------
# [실시간] API 데이터 로드 함수
# --------------------
@st.cache_data(ttl=120)  # 2분 캐싱
def fetch_realtime_standings():
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {
            "x-apisports-key": API_KEY
        }
        
        # 진짜 월드컵 ID '1'과 시즌 '2026' 매핑
        url = "https://v3.football.api-sports.io/standings?league=1&season=2026"
        
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        # 디버깅용 데이터 저장
        st.session_state["raw_api_debug"] = data
        
        if "response" not in data or not data["response"]:
            return pd.DataFrame(columns=["국가", "승점", "골득실", "득점"])
            
        standings_list = data["response"][0].get("league", {}).get("standings", [])
        
        all_teams_data = []
        
        for group in standings_list:
            if isinstance(group, list):
                for idx, team_info in enumerate(group):
                    team_obj = team_info.get("team", {})
                    eng_name = team_obj.get("name", "Unknown")
                    kor_name = COUNTRY_MAP.get(eng_name, eng_name)
                    
                    points = team_info.get("points", 0)
                    goals_diff = team_info.get("goalsDiff", 0)
                    
                    all_stats = team_info.get("all", {})
                    goals_stats = all_stats.get("goals", {})
                    goals_for = goals_stats.get("for", 0)
                    
                    group_rank = team_info.get("rank", idx + 1)
                    
                    all_teams_data.append({
                        "국가": kor_name,
                        "승점": points,
                        "골득실": goals_diff,
                        "득점": goals_for,
                        "조내순위": group_rank
                    })
                    
        full_df = pd.DataFrame(all_teams_data)
        
        if full_df.empty:
            return full_df
            
        # 각 조의 3위 팀만 추출
        third_place_df = full_df[full_df["조내순위"] == 3].copy()
        
        if third_place_df.empty:
            return full_df[["국가", "승점", "골득실", "득점"]]
            
        return third_place_df[["국가", "승점", "골득실", "득점"]]

    except Exception as e:
        st.sidebar.error(f"실시간 데이터 파싱 중 에러 발생: {e}")
        return pd.DataFrame(columns=["국가", "승점", "골득실", "득점"])


# ====================================================
# 2. 데이터 처리 메인 로직
# ====================================================
ranking_raw = fetch_realtime_standings()

if not ranking_raw.empty:
    ranking = calculate_rank(ranking_raw)
    korea_df = ranking[ranking["국가"].str.contains("대한민국|Korea", case=False)]
    
    if not korea_df.empty:
        korea = korea_df.iloc[0]
        has_korea_data = True
    else:
        has_korea_data = False
else:
    ranking = pd.DataFrame(columns=["국가", "승점", "골득실", "득점", "순위", "진출"])
    has_korea_data = False


# ====================================================
# 3. 메인 대시보드 화면 UI
# ====================================================
st.title("🇰🇷 대한민국 32강 진출 추적기")

if has_korea_data:
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 순위", f"조 3위 중 {int(korea['순위'])}위")
    col2.metric("진출 여부", "✅ 진출권" if korea["순위"] <= 8 else "❌ 탈락권")

    probability = {1:99, 2:97, 3:94, 4:90, 5:82, 6:72, 7:60, 8:51, 9:35, 10:20, 11:8, 12:1}
    col3.metric("예상 진출확률", f"{probability.get(int(korea['순위']), 0)}%")

    st.divider()

    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.subheader("📊 각 조 3위 팀 간 순위 비교 (와일드카드)")
        st.dataframe(ranking, use_container_width=True)

    with right_col:
        st.subheader("🇰🇷 대한민국 실시간 현황")
        st.write(
            f"""
            현재 대한민국은 **조 3위 팀 중 {int(korea['순위'])}위** 입니다.
            
            * **실시간 승점:** {int(korea['승점'])} 점
            * **실시간 골득실:** {int(korea['골득실'])}
            * **실시간 총 득점:** {int(korea['득점'])} 점
            """
        )

        st.subheader("📣 오늘 대한민국 응원팀")
        st.success("🇲🇦 모로코 (경쟁국 상대팀)")
        st.success("🇪🇸 스페인")
else:
    st.info("💡 현재 API 응답은 받아왔으나, 데이터 초기 상태이거나 아직 경기가 치러지지 않아 대한민국 정보를 별도로 추출할 수 없습니다.")
    
    st.subheader("📊 수집된 실시간 원본 데이터 상태")
    if not ranking_raw.empty:
        st.write("아래는 현재 API-Football에서 추출해낸 국가 목록입니다:")
        st.dataframe(ranking_raw, use_container_width=True)
    else:
        st.write("API에서 수집된 국가 데이터가 완전히 비어있습니다. 서버에 순위표 데이터가 아직 안 올라왔을 수 있습니다.")

    with st.expander("🔍 [개발자 모드] API 서버 실제 응답 구조(JSON) 보기"):
        if "raw_api_debug" in st.session_state:
            st.json(st.session_state["raw_api_debug"])
        else:
            st.write("서버 응답 기록이 존재하지 않습니다.")


# ====================================================
# 4. 사이드바 UI
# ====================================================
st.sidebar.title("🔧 API 관리 및 테스트")

if st.sidebar.button("API 연결 확인"):
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {"x-apisports-key": API_KEY}
        r = requests.get("https://v3.football.api-sports.io/status", headers=headers, timeout=10)
        st.sidebar.subheader("연결 상태 결과")
        st.sidebar.json(r.json())
    except Exception as e:
        st.sidebar.error(f"연결 실패: {e}")
