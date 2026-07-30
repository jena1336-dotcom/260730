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

# 1위 영화 지표 카드 (1위 영화명 굵게 강조)
top = df.sort_values("rank").iloc[0]
top1_movie_name = top["movieNm"]

c1, c2, c3 = st.columns(3)
c1.markdown(f"**어제 1위**  \n### 🔴 **{top1_movie_name}**")
c2.metric("어제 관객수", f"{top['audiCnt']:,}명")
c3.metric("누적 관객", f"{top['audiAcc']:,}명")

# 표를 한국어 열 이름으로 정리
table = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
table.columns = ["순위", "영화명", "개봉일", "관객수", "누적관객", "스크린수"]
table = table.sort_values("순위").reset_index(drop=True)

st.subheader("📋 박스오피스 TOP 10")
st.dataframe(table, use_container_width=True)

# -------------------------------------------------------------
# 📈 관객수 상위 5편 (원그래프 & 색상 지정)
# -------------------------------------------------------------
st.subheader("📈 관객수 상위 5편 비율")
top5 = table.sort_values("관객수", ascending=False).head(5).copy()

# 파스텔 톤 팔레트 (1위 제외 다른 영화용)
other_colors = ["#4D96FF", "#6BCB77", "#FFD93D", "#9B51E0", "#FF9F45"]

color_discrete_map = {}
for i, name in enumerate(top5["영화명"]):
    if name == top1_movie_name:
        color_discrete_map[name] = "#FF2A2A"  # 1위 영화는 선명한 빨간색
    else:
        color_discrete_map[name] = other_colors[i % len(other_colors)]

# 파이 차트 생성
fig = px.pie(
    top5,
    names="영화명",
    values="관객수",
    color="영화명",
    color_discrete_map=color_discrete_map,
    hole=0.3,  # 도넛 형태 연출 (0으로 설정하면 일반 파이 차트)
)

# 차트 내 텍스트 및 스타일 설정
fig.update_traces(
    textposition="inside",
    textinfo="label+percent",
    hovertemplate="<b>%{label}</b><br>관객수: %{value:,}명<br>비율: %{percent}",
)

fig.update_layout(
    margin=dict(l=20, r=20, t=30, b=20),
    legend_title_text="영화 제목",
    showlegend=True,
)

st.plotly_chart(fig, use_container_width=True)
