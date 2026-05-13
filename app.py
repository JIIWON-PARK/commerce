import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(
    page_title="서울시 상권 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 디자인 테마
st.markdown("""
<style>
.main { background-color: #f8f9fa; }
.stMetric {
    background-color: #ffffff;
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# 2. DB 연결 함수
def get_connection():
    db_path = 'commerce.db'
    if not os.path.exists(db_path):
        st.error(f"⚠️ '{db_path}' 파일이 없습니다. 경로를 확인해주세요!")
        st.stop()
    return sqlite3.connect(db_path)

@st.cache_data
def load_data(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# --- 사이드바 ---
with st.sidebar:
    st.title("🔍 검색 필터")
    st.info("보고 싶은 자치구를 선택하세요.")

    gu_list = load_data("SELECT 자치구명 FROM 자치구 ORDER BY 자치구명")['자치구명'].tolist()
    selected_gu = st.selectbox("자치구 선택", ["전체"] + gu_list)

    st.divider()
    st.caption("Data Source: 서울시공공데이터 상권분석")

# --- 메인 화면 ---
st.title("📊 서울시 자치구별 상권 분석")
st.markdown(f"### 📍 {selected_gu} 상권 현황")

# 종합 인사이트
if selected_gu == "전체":
    st.info("""
     
    2024년 서울시 상권은 전반적으로 주중 매출 비중이 높게 나타나, 주말 여가 소비보다 평일 업무·생활 소비 중심의 구조가 강합니다.  
    또한 자치구별 객단가와 경제활동인구 1명당 매출은 총매출 순위와 다르게 나타나, 단순 매출 규모뿐 아니라 소비 단가와 인구 대비 상권 활성도도 함께 볼 필요가 있습니다.  
    폐업 위험 업종은 일부 오락·교육·특수 소비 업종에서 높게 나타나, 업종별 안정성 차이도 확인할 수 있습니다. 
    
    """)
else:
    st.info(f"""
    인사이트
    
    현재 선택한 지역은 {selected_gu}입니다.  
    아래 차트에서는 {selected_gu}의 주중·주말 매출 구조, 폐업 위험 업종, 객단가 수준을 서울시 전체 자치구와 비교할 수 있습니다.  
    이를 통해 해당 자치구가 평일형 상권인지, 주말 소비 비중이 높은 상권인지, 또는 객단가와 인구 대비 매출 측면에서 경쟁력이 있는지를 확인할 수 있습니다.
    """)

where_clause = "" if selected_gu == "전체" else f"WHERE j.자치구명 = '{selected_gu}'"

# --- 섹션 1 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1️⃣ 주중 vs 주말 매출 비중")

    q1 = f"""
    SELECT 
        SUM(s.주중매출금액) AS 주중,
        SUM(s.주말매출금액) AS 주말
    FROM 상권매출 s
    JOIN 자치구 j ON s.자치구코드 = j.자치구코드
    {where_clause}
    """

    df1 = load_data(q1)

    if not df1.empty:
        fig1 = px.pie(
            names=['주중', '주말'],
            values=[df1.iloc[0]['주중'], df1.iloc[0]['주말']],
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig1.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig1, use_container_width=True)

        weekday_sales = df1.iloc[0]['주중'] if pd.notna(df1.iloc[0]['주중']) else 0
        weekend_sales = df1.iloc[0]['주말'] if pd.notna(df1.iloc[0]['주말']) else 0
        total_sales = weekday_sales + weekend_sales

        if total_sales > 0:
            weekday_ratio = weekday_sales / total_sales * 100
            weekend_ratio = weekend_sales / total_sales * 100

            if weekday_ratio > weekend_ratio:
                st.info(f"""
                인사이트  
                
                {selected_gu} 기준 주중 매출 비중은 {weekday_ratio:.1f}%, 주말 매출 비중은 {weekend_ratio:.1f}%입니다.  
                주중 매출 비중이 더 높아, 해당 상권은 평일 업무·생활 소비의 영향을 더 크게 받는 구조로 볼 수 있습니다.
                """)
            else:
                st.info(f"""
                인사이트  
                
                {selected_gu} 기준 주말 매출 비중은 {weekend_ratio:.1f}%, 주중 매출 비중은 {weekday_ratio:.1f}%입니다.  
                주말 매출 비중이 상대적으로 높아, 여가·방문 소비 성격이 강한 상권으로 해석할 수 있습니다.
                """)

with col2:
    st.subheader("2️⃣ 자치구별 객단가 순위")

    q3 = """
    SELECT 
        j.자치구명,
        ROUND(SUM(s.당월매출금액) * 1.0 / NULLIF(SUM(s.당월매출건수), 0), 0) AS 객단가
    FROM 상권매출 s
    JOIN 자치구 j ON s.자치구코드 = j.자치구코드
    GROUP BY j.자치구명
    ORDER BY 객단가 DESC
    """

    df3 = load_data(q3)
    df3['color'] = df3['자치구명'].apply(lambda x: '#EF553B' if x == selected_gu else '#636EFA')

    fig3 = px.bar(
        df3,
        x='자치구명',
        y='객단가',
        color='color',
        color_discrete_map="identity"
    )
    fig3.update_layout(showlegend=False, xaxis_title=None, yaxis_title="평균 결제 금액")
    st.plotly_chart(fig3, use_container_width=True)

    top_gu = df3.iloc[0]['자치구명']
    top_price = df3.iloc[0]['객단가']

    if selected_gu == "전체":
        st.info(f"""
        인사이트 
        
        2024년 기준 객단가가 가장 높은 자치구는 {top_gu}, 평균 객단가는 약 {top_price:,.0f}원입니다.  
        객단가는 총매출과 달리 1건당 평균 소비금액을 보여주므로, 고가 소비 업종이나 단가가 높은 상권의 특징을 파악하는 데 유용합니다.
        """)
    else:
        selected_row = df3[df3['자치구명'] == selected_gu]
        if not selected_row.empty:
            selected_price = selected_row.iloc[0]['객단가']
            selected_rank = selected_row.index[0] + 1
            st.info(f"""
            인사이트
            
            {selected_gu}의 객단가는 약 {selected_price:,.0f}원이며, 서울시 25개 자치구 중 {selected_rank}위입니다.  
            총매출 규모와 별개로, 해당 지역에서 한 번 결제할 때 평균적으로 어느 정도 소비가 발생하는지 확인할 수 있습니다.
            """)

st.divider()

# --- 섹션 2 ---
col3, col4 = st.columns(2)

with col3:
    st.subheader("3️⃣ 폐업 위험 업종 TOP 10")

    q2 = f"""
    SELECT 
        u.서비스업종명,
        ROUND(AVG(p.폐업율), 2) AS 평균폐업율
    FROM 점포현황 p
    JOIN 자치구 j ON p.자치구코드 = j.자치구코드
    JOIN 서비스업종 u ON p.서비스업종코드 = u.서비스업종코드
    {where_clause if where_clause else "WHERE 1=1"}
    GROUP BY u.서비스업종명
    HAVING SUM(p.점포수) >= 10
    ORDER BY 평균폐업율 DESC
    LIMIT 10
    """

    df2 = load_data(q2)

    fig2 = px.bar(
        df2,
        x='평균폐업율',
        y='서비스업종명',
        orientation='h',
        color='평균폐업율',
        color_continuous_scale='Reds'
    )
    fig2.update_layout(yaxis={'categoryorder': 'total ascending'}, xaxis_title="평균 폐업율 (%)")
    st.plotly_chart(fig2, use_container_width=True)

    if not df2.empty:
        top_industry = df2.iloc[0]['서비스업종명']
        top_close_rate = df2.iloc[0]['평균폐업율']

        if selected_gu == "전체":
            st.warning(f"""
            인사이트 
            
            서울시 전체 기준 폐업률이 가장 높게 나타난 업종은 {top_industry}이며, 평균 폐업률은 {top_close_rate:.2f}%입니다.  
            폐업률은 업종별 안정성을 보여주는 지표이지만, 점포 규모가 작은 업종은 수치가 크게 흔들릴 수 있으므로 점포 수와 함께 해석해야 합니다.
            """)
        else:
            st.warning(f"""
            인사이트
            
            {selected_gu}에서 폐업률이 가장 높게 나타난 업종은 {top_industry}이며, 평균 폐업률은 {top_close_rate:.2f}%입니다.  
            해당 업종은 선택 자치구 내에서 상대적으로 폐업 위험이 높은 업종으로 볼 수 있습니다.
            """)

with col4:
    st.subheader("4️⃣ 경제활동인구 1명당 매출")

    q4 = """
    WITH 매출집계 AS (
        SELECT 
            자치구코드,
            SUM(당월매출금액) AS 총매출
        FROM 상권매출
        GROUP BY 자치구코드
    ),
    인구반기 AS (
        SELECT 
            자치구코드,
            기준반기,
            SUM(경제활동인구수) AS 반기경제활동인구
        FROM 경제활동인구
        GROUP BY 자치구코드, 기준반기
    ),
    인구연평균 AS (
        SELECT 
            자치구코드,
            AVG(반기경제활동인구) AS 평균경제활동인구
        FROM 인구반기
        GROUP BY 자치구코드
    )
    SELECT 
        j.자치구명,
        ROUND(m.총매출 * 1.0 / NULLIF(p.평균경제활동인구 * 1000, 0), 0) AS 인당매출
    FROM 매출집계 m
    JOIN 인구연평균 p ON m.자치구코드 = p.자치구코드
    JOIN 자치구 j ON m.자치구코드 = j.자치구코드
    ORDER BY 인당매출 DESC
    """

    df4 = load_data(q4)

    fig4 = px.area(df4, x='자치구명', y='인당매출', title=None)
    fig4.update_traces(line_color='#00CC96', fillcolor='rgba(0, 204, 150, 0.2)')
    fig4.update_layout(xaxis_title=None, yaxis_title="1명당 매출")
    st.plotly_chart(fig4, use_container_width=True)

    top_pop_gu = df4.iloc[0]['자치구명']
    top_pop_sales = df4.iloc[0]['인당매출']

    if selected_gu == "전체":
        st.info(f"""
        인사이트
        
        경제활동인구 1명당 매출이 가장 높은 자치구는 {top_pop_gu}이며, 1명당 매출은 약 {top_pop_sales:,.0f}원입니다.  
        이 지표는 단순 총매출이 아니라 경제활동인구 규모 대비 상권이 얼마나 큰 매출을 만들어내는지를 보여줍니다.
        """)
    else:
        selected_pop = df4[df4['자치구명'] == selected_gu]
        if not selected_pop.empty:
            selected_pop_sales = selected_pop.iloc[0]['인당매출']
            selected_pop_rank = selected_pop.index[0] + 1
            st.info(f"""
            인사이트
            
            {selected_gu}의 경제활동인구 1명당 매출은 약 {selected_pop_sales:,.0f}원이며, 서울시 25개 자치구 중 {selected_pop_rank}위입니다.  
            이 값이 높을수록 해당 지역은 내부 경제활동인구 규모에 비해 상권 매출이 크게 형성된 지역으로 볼 수 있습니다.
            
            """)

st.caption("Data Source: 서울시 열린데이터광장 상권분석서비스, 경제활동인구 데이터")
