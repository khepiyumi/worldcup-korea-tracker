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
# [실시간] API 데이터 로드 함수 (인덱스 에러 완벽 방어)
# --------------------
@st.cache_data(ttl=300)  # 5분(300초) 동안 캐싱하여 API 호출 횟수 관리
def fetch_realtime_standings():
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {
            "x-apisports-key": API_KEY
        }
        
        # 2026 북중미 월드컵 리그 ID와 시즌 설정
        # (※ 사이드바의 '월드컵 리그 ID 찾기' 결과로 나온 ID를 1 대신 넣으시면 정확해집니다)
        url = "https://v3.football.api-sports.io/standings?league=1&season=2026"
        
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        # [방어 코드] 응답 데이터 구조가 유효한지 먼저 체크
        if "response" not in data or not data["response"]:
            return pd.DataFrame(columns=["국가", "승점", "골득실", "득점"])
            
        standings_list = data["response"][0].get("league", {}).get("standings", [])
        
        raw_data = []
        
        # 각 조(Group)를 순회하며 데이터 수집
        for group in standings_list:
            # [방어 코드] group이 리스트 형태이고, 조 3위(인덱스 2) 데이터가 실제로 존재하는지 체크
            if isinstance(group, list) and len(group) >= 3:
                team_info = group[2]  # 조 3위 팀 정보 안전하게 타깃팅
                
                # 안전하게 딕셔너리 내부 값 탐색 (.get 활용)
                team_obj = team_info.get("team", {})
                eng_name = team_obj.get("name", "Unknown")
                kor_name = COUNTRY_MAP.get(eng_name, eng_name) # 매핑 안 되어있으면 영문명 사용
                
                points = team_info.get("points", 0)
                goals_diff = team_info.get("goalsDiff", 0)
                
                # 득점 데이터 계층 안전하게 탐색
                all_stats = team_info.get("all", {})
                goals_stats = all_stats.get("goals", {})
                goals_for = goals_stats.get("for", 0)
                
                raw_data.append([kor_name, points, goals_diff, goals_for])
                
        # 데이터프레임 생성
        df = pd.DataFrame(raw_data, columns=["국가", "승점", "골득실", "득점"])
        return df

    except Exception as e:
        st.sidebar.error(f"실시간 데이터 파싱 중 에러 발생: {e}")
        return pd.DataFrame(columns=["국가", "승점", "골득실", "득점"])


# ====================================================
# 2. 데이터 처리 메인 로직
# ====================================================
# API 데이터 호출
ranking_raw = fetch_realtime_standings()

# 순위 계산 및 대한민국 데이터 필터링
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
    # --------------------
    # 상단 요약 (Metric)
    # --------------------
    col1, col2, col3 = st.columns(3)
    col1.metric("현재 순위", f"조 3위 중 {int(korea['순위'])}위")
    col2.metric("진출 여부", "✅ 진출권" if korea["순위"] <= 8 else "❌ 탈락권")

    # 순위별 진출 확률 가이드 맵
    probability = {1:99, 2:97, 3:94, 4:90, 5:82, 6:72, 7:60, 8:51, 9:35, 10:20, 11:8, 12:1}
    col3.metric("예상 진출확률", f"{probability.get(int(korea['순위']), 0)}%")

    st.divider()

    # --------------------
    # 본문 영역 (좌측: 순위표 / 우측: 상태 및 조건)
    # --------------------
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

        st.subheader("🎯 진출 조건")
        st.info(
            """
            대한민국보다 아래 순위 팀들이 승점을 획득하지 못할수록 유리합니다.
            특히 경쟁 관계에 있는 타 조의 결과들을 주목하세요.
            """
        )
else:
    # 데이터가 비어있거나 한국이 없을 때 노출되는 안전 화면
    st.info("💡 현재 API 응답에 조별리그 데이터가 없거나 경기가 시작되지 않아 대한민국 정보를 추출할 수 없습니다.")
    
    st.subheader("📊 수집된 실시간 원본 데이터 상태")
    if not ranking_raw.empty:
        st.dataframe(ranking_raw, use_container_width=True)
    else:
        st.write("API에서 가져온 데이터가 비어있습니다. 사이드바에서 리그 ID 및 API연결을 확인해주세요.")
        ascending=False
    ).reset_index(drop=True)

    df["순위"] = df.index + 1
    df["진출"] = df["순위"] <= 8  # 상위 8개팀 진출 자격

    return df


# --------------------
# [실시간] API 데이터 로드 함수
# --------------------
@st.cache_data(ttl=300)  # 5분(300초) 동안 캐싱하여 API 호출 횟수(과금)를 제한합니다.
def fetch_realtime_standings():
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {
            "x-apisports-key": API_KEY
        }
        
        # 2026 북중미 월드컵 리그 ID와 시즌 설정
        # (※ '월드컵 찾기' 결과로 나온 정확한 월드컵 league ID를 넣으셔야 합니다. 예시: 1)
        url = "https://v3.football.api-sports.io/standings?league=1&season=2026"
        
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        # API 응답 결과에서 조별 리그 순위 리스트 추출
        standings_list = data.get("response", [{}])[0].get("league", {}).get("standings", [])
        
        raw_data = []
        
        # 각 조(Group)를 순회하며 데이터 수집
        for group in standings_list:
            # 월드컵 규칙에 따라 각 조의 '3위 팀'만 와일드카드 경쟁 데이터셋에 추가
            # 만약 아직 3경기 조별리그가 끝나지 않아 순위 변동 중이라면 index 2(3번째) 팀을 타깃으로 잡습니다.
            if len(group) >= 3:
                team_info = group[2] # 조 3위 팀 정보
                
                eng_name = team_info["team"]["name"]
                kor_name = COUNTRY_MAP.get(eng_name, eng_name) # 매핑 딕셔너리에 없으면 영문명 그대로 사용
                
                points = team_info["points"]
                goals_diff = team_info["goalsDiff"]
                goals_for = team_info["all"]["goals"]["for"]
                
                raw_data.append([kor_name, points, goals_diff, goals_for])
                
        # 데이터프레임 생성
        df = pd.DataFrame(raw_data, columns=["국가", "승점", "골득실", "득점"])
        return df

    except Exception as e:
        st.error(f"실시간 API 데이터를 수집하는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(columns=["국가", "승점", "골득실", "득점"])


# ====================================================
# 2. 데이터 처리 메인 로직
# ====================================================
# API로부터 실시간 조 3위 데이터 가져오기
ranking_raw = fetch_realtime_standings()

# 데이터가 비어있지 않다면 순위 계산 진행
if not ranking_raw.empty:
    ranking = calculate_rank(ranking_raw)
    
    # 대한민국(또는 South Korea 포함 행) 찾기
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
    # --------------------
    # 상단 요약 (Metric)
    # --------------------
    col1, col2, col3 = st.columns(3)

    col1.metric("현재 순위", f"조 3위 중 {int(korea['순위'])}위")

    col2.metric("진출 여부", "✅ 진출권 (상위 8개국)" if korea["순위"] <= 8 else "❌ 탈락권")

    # 순위별 진출 확률 맵 (임시 가이드 데이터)
    probability = {1:99, 2:97, 3:94, 4:90, 5:82, 6:72, 7:60, 8:51, 9:35, 10:20, 11:8, 12:1}
    col3.metric("예상 진출확률", f"{probability.get(int(korea['순위']), 0)}%")

    st.divider()

    # --------------------
    # 본문 영역 (좌측: 순위표 / 우측: 상태 및 조건)
    # --------------------
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.subheader("📊 각 조 3위 팀 간 순위 비교 (와일드카드)")
        st.dataframe(ranking, use_container_width=True)

    with right_col:
        st.subheader("🇰🇷 대한민국 실시간 현황")
        # 문자열 앞에 f를 붙여 변수가 정상 대입되도록 수정했습니다.
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
        st.success("🇬🇭 가나")

        st.subheader("🎯 진출 조건")
        st.info(
            """
            대한민국보다 아래 순위 팀들이 승점을 획득하지 못할수록 유리합니다.
            특히 경쟁 관계에 있는 타 조의 결과들을 주목하세요.
            """
        )
else:
    st.info("현재 조별리그 데이터에서 '대한민국'을 찾을 수 없거나 아직 경기가 진행되지 않았습니다. 사이드바에서 API 연결 상태를 점검해보세요.")
    st.subheader("📊 실시간 전체 3위 데이터")
    st.dataframe(ranking_raw, use_container_width=True)


# ====================================================
# 4. 사이드바 UI (API 관리 및 디버깅 툴)
# ====================================================
st.sidebar.title("🔧 API 관리 및 테스트")

# 첫 번째 테스트 버튼: 기본적인 계정 및 토큰 상태 확인
if st.sidebar.button("API 연결 확인"):
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {"x-apisports-key": API_KEY}
        r = requests.get(
            "https://v3.football.api-sports.io/status",
            headers=headers,
            timeout=10
        )
        st.sidebar.subheader("연결 상태 결과")
        st.sidebar.json(r.json())
    except Exception as e:
        st.sidebar.error(f"연결 실패: {e}")

st.sidebar.divider()

# 두 번째 테스트 버튼: 리그 ID 식별용 헬퍼 버튼
if st.sidebar.button("월드컵 리그 ID 찾기"):
    try:
        API_KEY = st.secrets["API_FOOTBALL_KEY"]
        headers = {"x-apisports-key": API_KEY}
        r = requests.get(
            "https://v3.football.api-sports.io/leagues?search=World Cup",
            headers=headers,
            timeout=10
        )
        # 결과 출력이 메인 화면을 침범하여 UI를 깨뜨리지 않도록 사이드바 내부에 노출합니다.
        st.sidebar.subheader("월드컵 검색 결과")
        st.sidebar.json(r.json())
    except Exception as e:
        st.sidebar.error(f"검색 실패: {e}")
