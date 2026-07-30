import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import plotly.express as px

st.set_page_config(page_title="박스오피스 대시보드", layout="wide")
st.title("🎬 어제의 박스오피스")

# 비밀 금고에서 인증키 꺼내기
KOBIS_KEY = st.secrets["KOBIS_KEY"]

# 한국 시간 기준 어제 날짜를 여덟 자리로
yesterday = datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")
st.caption(f"조회 기준일(어제): {yesterday.strftime('%Y-%m-%d')}")

url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
res = requests.get(url, params={"key": KOBIS_KEY, "targetDt": target_dt}, timeout=10)

if res.status_code != 200:
    st.error(f"요청이 실패했습니다 (상태코드: {res.status_code})")
    st.stop()

data = res.json()

if "faultInfo" in data:
    st.error("인증키가 올바르지 않습니다. 금고(Secrets)의 KOBIS_KEY를 확인해 주세요.")
    st.stop()

box_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
if not box_list:
    st.warning("그날 자료가 없습니다. 날짜를 하루 더 앞으로 옮겨 보세요.")
    st.stop()

df = pd.DataFrame(box_list)

# 숫자 타입 변환
for col in ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]:
    df[col] = pd.to_numeric(df[col])

# 1위 영화 지표 카드 (텍스트 빨간색 + 굵게)
top = df.sort_values("rank").iloc[0]
top1_movie_name = top["movieNm"]

c1, c2, c3 = st.columns(3)
with c1:
    st.caption("어제 1위")
    st.markdown(f"<h3 style='color: #FF6B6B; font-weight: bold; margin: 0;'>{top1_movie_name}</h3>", unsafe_allow_html=True)
c2.metric("어제 관객수", f"{top['audiCnt']:,}명")
c3.metric("누적 관객", f"{top['audiAcc']:,}명")

# 표를 한국어 열 이름으로 정리
table = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
table.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
table = table.sort_values("순위").reset_index(drop=True)

st.subheader("📋 박스오피스 TOP 10")
st.dataframe(table, use_container_width=True)

# -------------------------------------------------------------
# 📈 관객수 상위 5편 (파스텔 톤 & 내부 글자 확대)
# -------------------------------------------------------------
st.subheader("📈 관객수 상위 5편 비율")
top5 = table.sort_values("관객수", ascending=False).head(5).copy()

# 파스텔 톤 팔레트 설정 (2~5위용)
pastel_colors = ["#A8DADC", "#457B9D", "#B8E0D2", "#F4A261", "#E8AEB7"]

color_discrete_map = {}
pastel_idx = 0
for name in top5["영화명"]:
    if name == top1_movie_name:
        color_discrete_map[name] = "#FF6B6B"  # 1위 영화: 은은하고 예쁜 파스텔 코랄 레드
    else:
        color_discrete_map[name] = pastel_colors[pastel_idx % len(pastel_colors)]
        pastel_idx += 1

# 파이 차트 생성
fig = px.pie(
    top5,
    names="영화명",
    values="관객수",
    color="영화명",
    color_discrete_map=color_discrete_map,
    hole=0.35,  # 도넛 스타일
)

# 차트 내 텍스트 및 글자 크기 변경
fig.update_traces(
    textposition="inside",
    textinfo="label+percent",
    textfont=dict(size=16, family="sans-serif", color="black"),  # 💡 글자 크기를 16pt로 확대
    hovertemplate="<b>%{label}</b><br>관객수: %{value:,}명<br>비율: %{percent}",
)

fig.update_layout(
    margin=dict(l=20, r=20, t=30, b=20),
    legend_title_text="영화 제목",
    legend=dict(font=dict(size=14)),  # 범례 글자 크기도 확대
    showlegend=True,
)

st.plotly_chart(fig, use_container_width=True)
