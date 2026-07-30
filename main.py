import re
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="전국 중학생 인구 변화 지도", layout="wide")
st.title("🗺️ 연도별 전국 중학생 인구 비율 변화")
st.caption("시군구별 중학생 인구 비율 (만 12세~14세 기준, 행정안전부 주민등록 인구)")

POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
GEO_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"


@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_population():
    return pd.read_csv(POP_URL, dtype={"코드": str})


@st.cache_data(show_spinner="지도 경계를 불러오는 중입니다...")
def load_geojson():
    return requests.get(GEO_URL, timeout=30).json()


df = load_population()
geojson = load_geojson()

# 1. '계_'로 시작하는 나이 열 및 중학생(만 12~14세) 열 추출
total_cols = [c for c in df.columns if c.startswith("계_")]


def age_of(col):
    m = re.match(r"계_(\d+)세", col)
    return int(m.group(1)) if m else None


middle_school_cols = [c for c in total_cols if age_of(c) is not None and 12 <= age_of(c) <= 14]

# 2. 동 단위 인구 합산
df["전체인구"] = df[total_cols].sum(axis=1)
df["중학생인구"] = df[middle_school_cols].sum(axis=1)

# 3. 연도별 + 시군구별 그룹화 (최신 연도 필터링을 제거하고 연도도 그룹에 포함)
df["시군구코드"] = df["코드"].str[:5]
grouped = df.groupby(["연도", "시군구코드"])[["전체인구", "중학생인구"]].sum().reset_index()
grouped["중학생비율"] = (grouped["중학생인구"] / grouped["전체인구"] * 100).round(2)

# 연도순으로 정렬 (애니메이션 프레임 순서 보장)
grouped = grouped.sort_values("연도")

# 경계 파일에서 시군구·시도 이름 짝 만들기
names = pd.DataFrame([
    {
        "시군구코드": str(f["properties"]["코드"]),
        "시군구": f["properties"]["시군구"],
        "시도": f["properties"]["시도"],
    }
    for f in geojson["features"]
])
merged = grouped.merge(names, on="시군구코드", how="left")

# 4. 전체 연도 기간의 최소/최대 비율을 구해서 색상 범위(range_color)를 고정
# (연도가 바뀌어도 색상 기준이 일정해야 변화를 올바르게 비교할 수 있습니다)
min_rate = merged["중학생비율"].min()
max_rate = merged["중학생비율"].max()

# 5. 애니메이션 지도 그리기 (animation_frame="연도" 지정)
fig = px.choropleth(
    merged,
    geojson=geojson,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="중학생비율",
    animation_frame="연도",  # 연도별 프레임 생성
    color_continuous_scale=["#2b83ba", "#abdda4", "#ffffbf", "#fdae61", "#d7191c"],
    range_color=[min_rate, max_rate],  # 전 연도 공통 색상 범위 지정
    hover_name="시군구",
    hover_data={"중학생비율": True, "시도": True, "시군구코드": False, "연도": True},
    labels={"중학생비율": "중학생 비율(%)"},
)

fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin=dict(l=0, r=0, t=10, b=0),
    height=700,
    coloraxis_colorbar=dict(title="중학생 비율 (%)"),
)

# 애니메이션 속도 조절 (프레임당 500ms)
if fig.layout.updatemenus:
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 500

st.plotly_chart(fig, width="stretch")

# 6. 하단 순위 표 (슬라이더로 연도를 선택하여 조회)
st.markdown("---")
years = sorted(merged["연도"].unique())
selected_year = st.select_slider("📅 순위를 조회할 연도를 선택하세요", options=years, value=years[-1])

year_df = merged[merged["연도"] == selected_year]

c1, c2 = st.columns(2)
cols = ["시도", "시군구", "중학생비율"]


def get_ranked_df(data, ascending=False):
    res = data.nlargest(10, "중학생비율")[cols] if not ascending else data.nsmallest(10, "중학생비율")[cols]
    res = res.reset_index(drop=True)
    res.index = res.index + 1  # 1부터 시작하는 인덱스
    return res


with c1:
    st.subheader(f"🔴 {selected_year}년 중학생 비율 높은 곳 10")
    st.dataframe(get_ranked_df(year_df, ascending=False))

with c2:
    st.subheader(f"🔵 {selected_year}년 중학생 비율 낮은 곳 10")
    st.dataframe(get_ranked_df(year_df, ascending=True))
