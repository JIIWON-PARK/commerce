import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
import plotly.graph_objects as go

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="서울시 상권 분석 대시보드", layout="wide")
st.title("📊 2024 서울시 자치구별 상권 분석")
st.markdown("공공데이터를 활용하여 자치구별 매출과 폐업 위험도를 분석합니다.")

# 2. 데이터베이스 연결 확인 (에러 메시지 처리)
DB_PATH = 'commerce.db'

def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"❌ '{DB_PATH}' 파일을 찾을 수 없습니다. 데이터베이스 파일이 같은 폴더에 있는지 확인해주세요!")
        st.stop()
    return sqlite3.connect(DB_PATH)

# 데이터 로드 함수
@st.cache_data
def run_query(query):
    conn = get_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# 3. 사이드바: 자치구 선택 필터
st.sidebar.header("🔍 분석 필터")
districts_df = run_query("SELECT 자치구명 FROM 자치구 ORDER BY 자치구명")
selected_district = st.sidebar.selectbox("자치구를 선택하세요", ["전체"] + list(districts_df['자치구명']))

# --- 시각화 섹션 ---

# 1번: 주중 vs 주말 매출 비교 (원형 그래프)
st.subheader("1️⃣ 주중/주말 매출 비중")
q1_query = f"""
SELECT 
    SUM(s.주중매출금액) AS 주중매출금액,
    SUM(s.주말매출금액) AS 주말매출금액
FROM 상권매출 s
JOIN 자치구 j ON s.자치구코드 = j.자치구코드
{f"WHERE j.자치구명 = '{selected_district}'" if selected_district != '전체' else ""}
"""
q1_data = run_query(q1_query)
if not q1_data.empty:
    labels = ['주중 매출', '주말 매출']
    values = [q1_data.iloc[0]['주중매출금액'], q1_data.iloc[0]['주말매출금액']]
    fig1 = px.pie(names=labels, values=values, hole=0.4, color_discrete_sequence=['#636EFA', '#EF553B'])
    st.plotly_chart(fig1, use_container_width=True)

# 2번 & 3번 섹션 (2단 구성)
col1, col2 = st.columns(2)

with col1:
    # 2번: 폐업 위험도 (가로 막대 그래프)
    st.subheader("2️⃣ 업종별 평균 폐업률 (TOP 10)")
    q2_query = f"""
    SELECT j.자치구명, u.서비스업종명, ROUND(AVG(p.폐업율), 2) AS 평균폐업율
    FROM 점포현황 p
    JOIN 자치구 j ON p.자치구코드 = j.자치구코드
    JOIN 서비스업종 u ON p.서비스업종코드 = u.서비스업종코드
    WHERE 1=1 {f"AND j.자치구명 = '{selected_district}'" if selected_district != '전체' else ""}
    GROUP BY j.자치구명, u.서비스업종명
    HAVING SUM(p.점포수) >= 10
    ORDER BY 평균폐업율 DESC LIMIT 10
    """
    q2_data = run_query(q2_query)
    fig2 = px.bar(q2_data, x='평균폐업율', y='서비스업종명', orientation='h', 
                  title=f"{selected_district} 인기/위험 업종", color='평균폐업율', color_continuous_scale='Reds')
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    # 3번: 객단가 분석 (세로 막대 그래프)
    st.subheader("3️⃣ 자치구별 객단가")
    q3_query = """
    SELECT j.자치구명, ROUND(SUM(s.당월매출금액) * 1.0 / NULLIF(SUM(s.당월매출건수), 0), 0) AS 객단가
    FROM 상권매출 s
    JOIN 자치구 j ON s.자치구코드 = j.자치구코드
    GROUP BY j.자치구명 ORDER BY 객단가 DESC
    """
    q3_data = run_query(q3_query)
    # 선택된 구는 강조색 표시
    colors = ['#636EFA'] * len(q3_data)
    if selected_district != '전체':
        idx = q3_data[q3_data['자치구명'] == selected_district].index
        if not idx.empty: colors[idx[0]] = 'orange'
    
    fig3 = px.bar(q3_data, x='자치구명', y='객단가', title="자치구별 평균 결제 금액", color_discrete_sequence=[colors])
    st.plotly_chart(fig3, use_container_width=True)

# 4번: 경제활동인구 1명당 매출 (영역형/라인 그래프 추천)
st.subheader("4️⃣ 경제활동인구 1명당 매출액 (생산성 지표)")
q4_query = """
WITH 매출집계 AS (SELECT 자치구코드, SUM(당월매출금액) AS 총매출금액 FROM 상권매출 GROUP BY 자치구코드),
인구연평균 AS (SELECT 자치구코드, AVG(인구수) AS 평균인구 FROM (
    SELECT 자치구코드, SUM(경제활동인구수) AS 인구수 FROM 경제활동인구 GROUP BY 자치구코드, 기준반기
) GROUP BY 자치구코드)
SELECT j.자치구명, ROUND(m.총매출금액 * 1.0 / NULLIF(p.평균인구 * 1000, 0), 0) AS 인당매출
FROM 매출집계 m
JOIN 인구연평균 p ON m.자치구코드 = p.자치구코드
JOIN 자치구 j ON m.자치구코드 = j.자치구코드
ORDER BY 인당매출 DESC
"""
q4_data = run_query(q4_query)
fig4 = px.line(q4_data, x='자치구명', y='인당매출', markers=True, title="인구 대비 상권 활성화 정도")
fig4.update_traces(fill='tozeroy') # 영역 채우기 효과
st.plotly_chart(fig4, use_container_width=True)

st.caption("Data Source: 서울시 열린데이터광장 상권분석서비스 (2024)")