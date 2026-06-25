import streamlit as st
import pandas as pd
import requests

st.sidebar.title("API 테스트")

if st.sidebar.button("API 연결 확인"):

    API_KEY = st.secrets["API_FOOTBALL_KEY"]

    headers = {
        "x-apisports-key": API_KEY
    }

    r = requests.get(
        "https://v3.football.api-sports.io/status",
        headers=headers,
        timeout=30
    )

    st.write(r.json())

st.set_page_config(
    page_title="대한민국 32강 진출 추적기",
    layout="wide"
)

# --------------------
# 순위 계산 함수
# --------------------
def calculate_rank(df):

    df = df.sort_values(
        ["승점", "골득실", "득점"],
        ascending=False
    ).reset_index(drop=True)

    df["순위"] = df.index + 1
    df["진출"] = df["순위"] <= 8

    return df


# --------------------
# 샘플 데이터
# 나중에 API로 교체
# --------------------
ranking = pd.DataFrame(
    [
        ["보스니아",4,-1,5],
        ["스웨덴",4,0,6],
        ["알제리",4,0,4],
        ["크로아티아",3,-1,3],
        ["대한민국",3,-1,2],
        ["스코틀랜드",3,-3,1],
        ["벨기에",2,-2,2],
        ["튀니지",2,-3,1],
    ],
    columns=[
        "국가",
        "승점",
        "골득실",
        "득점"
    ]
)

ranking = calculate_rank(ranking)

korea = ranking[
    ranking["국가"] == "대한민국"
].iloc[0]

# --------------------
# 제목
# --------------------
st.title("🇰🇷 대한민국 32강 진출 추적기")

# --------------------
# 상단 요약
# --------------------
col1, col2, col3 = st.columns(3)

col1.metric(
    "현재 순위",
    f"{int(korea['순위'])}위"
)

col2.metric(
    "진출 여부",
    "✅ 진출권"
    if korea["순위"] <= 8
    else "❌ 탈락권"
)

# 임시 확률
probability = {
    1:99,
    2:97,
    3:94,
    4:90,
    5:82,
    6:72,
    7:60,
    8:51,
    9:35,
    10:20,
    11:8,
    12:1
}

col3.metric(
    "예상 진출확률",
    f"{probability.get(int(korea['순위']),0)}%"
)

st.divider()

# --------------------
# 3위 팀 순위
# --------------------
st.subheader("📊 3위 팀 순위")

st.dataframe(
    ranking,
    use_container_width=True
)

# --------------------
# 응원팀
# --------------------
st.subheader("📣 오늘 대한민국 응원팀")

st.success("🇯🇵 일본")
st.success("🇪🇸 스페인")
st.success("🇬🇭 가나")

# --------------------
# 진출 조건
# --------------------
st.subheader("🎯 진출 조건")

st.info(
"""
대한민국보다 아래 순위 팀들이
승점을 획득하지 못할수록 유리합니다.

특히 크로아티아, 벨기에,
튀니지 결과를 주목하세요.
"""
)

# --------------------
# 현재 상태
# --------------------
st.subheader("🇰🇷 대한민국 현황")

st.write(
    f"""
    현재 대한민국은
    **3위 팀 중 {int(korea['순위'])}위** 입니다.

    승점: {int(korea['승점'])}

    골득실: {int(korea['골득실'])}

    득점: {int(korea['득점'])}
    """
)
