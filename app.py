import streamlit as st
import pandas as pd
import numpy as np
import datetime
import yfinance as yf

# 페이지 설정
st.set_page_config(page_title="BAA 동적 자산배분 신호기", layout="wide")

st.title("📊 BAA(Breadth Momentum) 실시간 리밸런싱 대시보드")
st.markdown("매월 말 카나리아 자산(TIP)과 각 자산군의 모멘텀을 분석하여 실시간 투자 비중을 계산합니다.")

# 자산군 정의
offensive_assets = ["QQQ", "VEU", "VWO", "TLT", "IEF", "DBC", "VNQ"]
defensive_assets = ["IEF", "BIL"]
all_assets = ["QQQ", "VEU", "VWO", "TLT", "IEF", "DBC", "VNQ", "BIL", "TIP"]

@st.cache_data(ttl=14400)  # 4시간 동안 데이터 캐싱하여 속도 최적화
def load_financial_data(tickers):
    # 모멘텀 계산을 위해 2년치 데이터 수집
    start_date = (datetime.date.today() - datetime.timedelta(days=365*2)).strftime('%Y-%m-%d')
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    df = yf.download(tickers, start=start_date, end=end_date)
    if 'Close' in df.columns:
        df = df['Close']
    df = df.dropna()
    return df

try:
    with st.spinner('야후 파이낸스에서 최신 데이터를 가져오는 중입니다...'):
        data = load_financial_data(all_assets)
        
    # 월말 데이터 추출 (안전하게 처리)
    month_data = data.resample('M').last()
    
    if len(month_data) < 13:
        st.error("모멘텀 점수를 산출하기 위한 과거 데이터(최소 13개월)가 부족합니다.")
    else:
        # 가장 최근 영업일 데이터 기준
        latest_date = month_data.index[-1].strftime('%Y년 %m월 %d일')
        st.subheader(f"📅 실시간 분석 기준일: {latest_date}")
        
        # 모멘텀 스코어 계산 함수 (1, 3, 6, 9, 12개월 수익률의 합)
        def get_momentum_score(series, idx=-1):
            m1 = (series.iloc[idx] - series.iloc[idx-1]) / series.iloc[idx-1]
            m3 = (series.iloc[idx] - series.iloc[idx-3]) / series.iloc[idx-3]
            m6 = (series.iloc[idx] - series.iloc[idx-6]) / series.iloc[idx-6]
            m9 = (series.iloc[idx] - series.iloc[idx-9]) / series.iloc[idx-9]
            m12 = (series.iloc[idx] - series.iloc[idx-12]) / series.iloc[idx-12]
            return m1 + m3 + m6 + m9 + m12

        # 1. 카나리아 자산(TIP) 모멘텀 체크
        tip_score = get_momentum_score(month_data["TIP"])
        
        # 화면 레이아웃 분할
        col1, col2 = st.columns([1, 2])
        
        buy_allocation = {}
        market_status = ""
        
        with col1:
            st.metric(label="🎗️ TIP (카나리아 자산) 모멘텀 스코어", value=f"{tip_score:.4f}")
            
            if tip_score > 0:
                market_status = "공격형 자산 매수 국면 (Bull Market)"
                st.success(f"📈 **시장 국면:** {market_status}")
                
                # 공격형 자산 점수 계산
                off_scores = {asset: get_momentum_score(month_data[asset]) for asset in offensive_assets}
                off_series = pd.Series(off_scores).sort_values(ascending=False)
                top4 = off_series.nlargest(4)
                
                for asset in top4.index:
                    buy_allocation[asset] = "25.0%"
            else:
                market_status = "방어형 자산 매수 국면 (Bear Market)"
                st.warning(f"📉 **시장 국면:** {market_status}")
                
                # 방어형 자산 점수 계산
                def_scores = {asset: get_momentum_score(month_data[asset]) for asset in defensive_assets}
                def_series = pd.Series(def_scores).sort_values(ascending=False)
                top1 = def_series.nlargest(1)
                
                buy_allocation[top1.index[0]] = "100.0%"
        
        with col2:
            st.subheader("🎯 이번 달 최종 리밸런싱 추천 비중")
            portfolio_df = pd.DataFrame(list(buy_allocation.items()), columns=['추천 자산 (Ticker)', '목표 비중'])
            st.table(portfolio_df)
            
        # 전체 자산 현황 요약
        st.divider()
        st.subheader("🔍 전체 자산별 모멘텀 스코어 순위")
        
        all_scores = {asset: get_momentum_score(month_data[asset]) for asset in all_assets}
        df_scores = pd.DataFrame(list(all_scores.items()), columns=['자산 Ticker', '모멘텀 스코어']).set_index('자산 Ticker')
        df_scores = df_scores.sort_values(by='모멘텀 스코어', ascending=False)
        
        # 차트와 표 시각화
        chart_col, table_col = st.columns(2)
        with chart_col:
            st.bar_chart(df_scores)
        with table_col:
            st.dataframe(df_scores.style.format("{:.4f}"), use_container_width=True)

except Exception as e:
    st.error(f"데이터 로드 및 계산 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. 오류 내용: {e}")
