import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# 1. 페이지 설정 (심플하고 넓게)
st.set_page_config(page_title="서울시 상권 대시보드", layout="wide", initial_sidebar_state="expanded")

# 디자인 테마 적용 (CSS)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# 2. 데이터베이스 연결 함수 (에러 처리 포함)
def get_connection():
    db_path = 'commerce.db'
    if not os.path.exists(db_path):
        st.error(f"⚠️ '{db_path}' 파일이 없습니다. 경로를 확인해주세요!")
        st.stop()
    return sqlite3.connect(db_path)

# 데이터 로드 (캐싱으로 속도 향상)
@st.cache_data
def load_data(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# --- 사이드바: 깔끔한 필터 영역 ---
with st.sidebar:
    st.title("🔍 검색 필터")
    st.info("보고 싶은 자치구를 선택하세요.")
    
    # 자치구 목록 가져오기
    gu_list = load_data("SELECT 자치구명 FROM 자치구 ORDER BY 자치구명")['자치구명'].tolist()
    selected_gu = st.selectbox("자치구 선택", ["전체"] + gu_list)
    st.divider()
    st.caption("Data Source: 서울시 상권분석 서비스")

# --- 메인 화면 시작 ---
st.title("📊 서울시 자치구별 상권 분석")
st.markdown(f"### 📍 {selected_gu} 상권 현황")

# 필터링 조건 설정
where_clause = "" if selected_gu == "전체" else f"WHERE j.자치구명 = '{selected_gu}'"

# --- 섹션 1: 주중/주말 매출 및 객단가 (요약 지표) ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ 주중 vs 주말 매출 비중")
    q1 = f"""
    SELECT SUM(s.주중매출금액) AS 주중, SUM(s.주말매출금액) AS 주말
    FROM 상권매출 s JOIN 자치구 j ON s.자치구코드 = j.자치구코드 {where_clause}
    """
    df1 = load_data(q1)
    if not df1.empty:
        fig1 = px.pie(names=['주중', '주말'], values=[df1.iloc[0]['주중'], df1.iloc[0]['주말']], 
                     hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig1.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("3️⃣ 자치구별 객단가 순위")
    q3 = """
    SELECT j.자치구명, ROUND(SUM(s.당월매출금액) * 1.0 / NULLIF(SUM(s.당월매출건수), 0), 0) AS 객단가
    FROM 상권매출 s JOIN 자치구 j ON s.자치구코드 = j.자치구코드
    GROUP BY j.자치구명 ORDER BY 객단가 DESC
    """
    df3 = load_data(q3)
    # 선택된 자치구 강조색
    df3['color'] = df3['자치구명'].apply(lambda x: '#EF553B' if x == selected_gu else '#636EFA')
    fig3 = px.bar(df3, x='자치구명', y='객단가', color='color', color_discrete_map="identity")
    fig3.update_layout(showlegend=False, xaxis_title=None, yaxis_title="평균 결제 금액")
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# --- 섹션 2: 폐업 위험 및 인구당 매출 ---
col3, col4 = st.columns(2)

with col3:
    st.subheader("2️⃣ 폐업 위험 업종 (TOP 10)")
    q2 = f"""
    SELECT u.서비스업종명, ROUND(AVG(p.폐업율), 2) AS 평균폐업율
    FROM 점포현황 p JOIN 자치구 j ON p.자치구코드 = j.자치구코드
    JOIN 서비스업종 u ON p.서비스업종코드 = u.서비스업종코드
    {where_clause.replace('j.', 'j.') if where_clause else "WHERE 1=1"}
    GROUP BY u.서비스업종명 HAVING SUM(p.점포수) >= 10
    ORDER BY 평균폐업율 DESC LIMIT 10
    """
    df2 = load_data(q2)
    fig2 = px.bar(df2, x='평균폐업율', y='서비스업종명', orientation='h', 
                  color='평균폐업율', color_continuous_scale='Reds')
    fig2.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="평균 폐업율 (%)")
    st.plotly_chart(fig2, use_container_width=True)

with col4:
    st.subheader("4️⃣ 인구 1명당 창출 매출")
    q4 = """
    WITH 매출집계 AS (SELECT 자치구코드, SUM(당월매출금액) AS 총매출 FROM 상권매출 GROUP BY 자치구코드),
    인구 AS (SELECT 자치구코드, AVG(경제활동인구수) AS 평균인구 FROM 경제활동인구 GROUP BY 자치구코드)
    SELECT j.자치구명, ROUND(m.총매출 * 1.0 / NULLIF(p.평균인구 * 1000, 0), 0) AS 인당매출
    FROM 매출집계 m JOIN 인구 p ON m.자치구코드 = p.자치구코드
    JOIN 자치구 j ON m.자치구코드 = j.자치구코드 ORDER BY 인당매출 DESC
    """
    df4 = load_data(q4)
    fig4 = px.area(df4, x='자치구명', y='인당매출', title=None)
    fig4.update_traces(line_color='#00CC96', fillcolor='rgba(0, 204, 150, 0.2)')
    st.plotly_chart(fig4, use_container_width=True)
