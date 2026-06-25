import streamlit as st
import pandas as pd
import requests

# ====================================================
# 1. 페이지 및 기본 매핑 설정
# ====================================================
st.set_page_config(
    page_title="2026 북중미 월드컵 실시간 와일드카드 계산기",
    layout="wide"
)

COUNTRY_MAP = {
    "South Korea": "대한민국", "Korea Republic": "대한민국", "Korea": "대한민국",
    "Mexico": "멕시코", "Czech Republic": "체코", "Czechia": "체코",
    "South Africa": "남아공", "France": "프랑스", "Argentina": "아르헨티나"
}

# ----------------------------------------------------
# 2. [핵심] 경기 결과 데이터를 기반으로 실시간 순위표 자동 연산
# ----------------------------------------------------
@st.cache_data(ttl=60)
def build_standings_from_fixtures():
    # 기본 구조 선언
    teams_dict = {}
    
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {"x-apisports-key": API_KEY}
        # 2026 월드컵의 전체 매치 데이터 호출
        url = "https://v3.football.api-sports.io/fixtures?league=1&season=2026"
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        fixtures = data.get("response", [])
        
        if not fixtures:
            return pd.DataFrame()
            
        for f in fixtures:
            # API에서 각 매치의 조 정보 추출 (예: "Group A")
            group_raw = f.get("league", {}).get("round", "알 수 없는 조")
            if "Group" not in group_raw:
                continue
            group_name = group_raw.replace("Group ", "") + "조"
            if group_name == "A조":
                group_name = "대한민국 속한 조 (A조)"
            
            home_team = f["teams"]["home"]["name"]
            away_team = f["teams"]["away"]["name"]
            
            # 국문 매핑
            home_kor = COUNTRY_MAP.get(home_team, home_team)
            away_kor = COUNTRY_MAP.get(away_team, away_team)
            
            # 초기화
            for t in [home_kor, away_kor]:
                if t not in teams_dict:
                    teams_dict[t] = {"국가": t, "조": group_name, "승점": 0, "경기수": 0, "득점": 0, "실점": 0, "골득실": 0}
                    
            # 경기 스코어 확인
            home_goals = f["goals"]["home"]
            away_goals = f["goals"]["away"]
            
            # 경기가 진행되었거나 종료된 경우만 데이터 축적 (실시간 스코어 자동 반영)
            if home_goals is not None and away_goals is not None:
                teams_dict[home_kor]["경기수"] += 1
                teams_dict[away_kor]["경기수"] += 1
                teams_dict[home_kor]["득점"] += home_goals
                teams_dict[home_kor]["실점"] += away_goals
                teams_dict[away_kor]["득점"] += away_goals
                teams_dict[away_kor]["실점"] += home_goals
                
                # 승점 계산
                if home_goals > away_goals:
                    teams_dict[home_kor]["승점"] += 3
                elif home_goals < away_goals:
                    teams_dict[away_kor]["승점"] += 3
                else:
                    teams_dict[home_kor]["승점"] += 1
                    teams_dict[away_kor]["승점"] += 1

        # 데이터프레임 변환 후 골득실 연산
        df = pd.DataFrame(teams_dict.values())
        df["골득실"] = df["득점"] - df["실점"]
        df["남은경기"] = 3 - df["경기수"]
        return df

    except Exception as e:
        return pd.DataFrame()

# ----------------------------------------------------
# 3. 데이터 정렬 및 와일드카드(3위) 가리기
# ----------------------------------------------------
def process_data(df):
    if df.empty:
        return df, pd.DataFrame()
        
    ordered_groups = []
    third_places = []
    
    for g in df["조"].unique():
        g_df = df[df["조"] == g].copy()
        # 월드컵 공식 타이브레이커 규칙 (승점 -> 골득실 -> 다득점 순 정렬)
        g_df = g_df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
        g_df["조내순위"] = g_df.index + 1
        ordered_groups.append(g_df)
        
        # 조 3위 데이터 분리
        if len(g_df) >= 3:
            third_places.append(g_df.iloc[2])
            
    full_ordered = pd.concat(ordered_groups).reset_index(drop=True)
    
    # 와일드카드 순위 매기기 (전체 조 3위 중 상위 8개 팀 진출)
    third_df = pd.DataFrame(third_places)
    if not third_df.empty:
        third_df = third_df.sort_values(["승점", "골득실", "득점"], ascending=False).reset_index(drop=True)
        third_df["와일드카드 순위"] = third_df.index + 1
        third_df["32강 진출"] = third_df["와일드카드 순위"] <= 8
    
    return full_ordered, third_df

# ====================================================
# 4. 메인 대시보드 화면 출력
# ====================================================
st.title("⚽ 2026 북중미 월드컵 실시간 32강 와일드카드 계산기")
st.caption("본 대시보드는 경기 결과 API 피드를 실시간으로 분석하여 전체 조 편성 및 순위를 역추적합니다.")

raw_data = build_standings_from_fixtures()

if not raw_data.empty:
    all_groups, wildcard_rank = process_data(raw_data)
    
    # 대한민국 상황 체크
    korea_info = all_groups[all_groups["국가"] == "대한민국"]
    if not korea_info.empty:
        k = korea_info.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("대한민국 조내 순위", f"{int(k['조내순위'])}위 ({k['조']})")
        
        if k['조내순위'] <= 2:
            col2.metric("32강 진출 자격", "✅ 자력 진출 확정")
        else:
            # 3위일 때 와일드카드 테이블 안에서의 현재 등수 표시
            k_wc = wildcard_rank[wildcard_rank["국가"] == "대한민국"]
            wc_idx = int(k_wc.iloc[0]["와일드카드 순위"]) if not k_wc.empty else 99
            col2.metric("32강 진출 자격", f"⚠️ 와일드카드 경합 중 ({wc_idx}위)")
            
        col3.metric("승점 / 골득실", f"{int(k['승점'])}점 / {int(k['골득실'])}")
    
    st.divider()
    
    # [섹션 1] 전체 조 3위 와일드카드 순위표
    st.subheader("📊 각 조 3위 팀 간 와일드카드 순위비교 (상위 8개국 진출)")
    st.dataframe(
        wildcard_rank[["와일드카드 순위", "조", "국가", "승점", "골득실", "득점", "남은경기", "32강 진출"]], 
        use_container_width=True, hide_index=True
    )
    
    st.divider()
    
    # [섹션 2] API 경기결과로 자동 파싱된 전 조 실시간 순위표
    st.subheader("🔍 2026 월드컵 전 조 실시간 순위 현황")
    group_names = all_groups["조"].unique()
    cols = st.columns(3)
    
    for idx, g_name in enumerate(group_names):
        with cols[idx % 3]:
            st.markdown(f"### 📍 {g_name}")
            g_table = all_groups[all_groups["조"] == g_name][["조내순위", "국가", "승점", "골득실", "득점", "남은경기"]]
            st.dataframe(g_table, use_container_width=True, hide_index=True)
else:
    st.error("API 서버에서 월드컵 매치업 데이터를 받아오지 못했습니다. st.secrets의 API 키를 점검해 주세요.")
