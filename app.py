import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="대한민국 32강 진출 추적기",
    layout="wide"
)

st.title("🇰🇷 대한민국 32강 진출 추적기")

col1, col2, col3 = st.columns(3)

col1.metric(
    "현재 순위",
    "5위"
)

col2.metric(
    "진출 여부",
    "✅ 진출권"
)

col3.metric(
    "진출 확률",
    "72%"
)

st.divider()

ranking = pd.DataFrame(
    [
        ["보스니아",4,-1,5],
        ["스웨덴",4,0,6],
        ["대한민국",3,-1,2],
        ["스코틀랜드",3,-3,1],
    ],
    columns=[
        "국가",
        "승점",
        "골득실",
        "득점"
    ]
)

st.subheader("3위 팀 순위")

st.dataframe(
    ranking,
    use_container_width=True
)

st.subheader("📣 오늘 응원해야 할 팀")

st.success("일본")
st.success("스페인")
st.success("가나")

st.subheader("진출 조건")

st.info(
"""
한국보다 아래 팀들의
승점 획득을 최소화해야 합니다.
"""
)
