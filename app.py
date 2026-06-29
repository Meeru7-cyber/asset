import streamlit as st
import pandas as pd
import numpy as np
import datetime
import yfinance as yf

# 페이지 기본 설정
st.set_page_config(page_title="BAA 멀티 전략 대시보드", layout="wide")

st.title("📊 BAA(Breadth Momentum) 실시간 리밸런싱 대시보드")
st.markdown("매월 말 카나리아 자산(TIP)을 기준으로 시장 국면을 파악하여 포트폴리오 비중을 결정합니다.")

# ----------------------------------------------------
# 1. 자산군 정의
# ----------------------------------------------------
# 전략 1: 오리지널 BAA
strat1_off = ["QQQ", "VEU", "VWO", "TLT", "IEF", "DBC", "VNQ"]
strat1_def = ["IEF", "BIL"]

# 전략 2: 섹터 BAA (바이오, 테크, 클라우드, 반도체 등)
strat2_off = ["IBB", "IGV", "SKYY", "SOXX", "XLE", "XRT", "IEF", "DBC"]
strat2_def = ["IEF", "BIL"]

# 중복을 제거한 전체 티커 리스트 (데이터를 한 번에 불러오기 위함)
all_tickers = list(set(strat1_off + strat1_def + strat2_off + strat2_def + ["TIP"]))

# ----------------------------------------------------
# 2. 데이터 로드 및 전처리
# ----------------------------------------------------
@st.cache_data(ttl=14400) # 4시간 캐싱
def load_financial_data(tickers):
    start_date = (datetime.date.today() - datetime.timedelta(days=365*2)).strftime('%Y-%m-%d')
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    df = yf.download(tickers, start=start_date, end=end_date)
    if 'Close' in df.columns:
        df = df['Close']
    df = df.dropna()
    return df

# 모멘텀 스코어 계산 함수 (최근 1,3,6,9,12개월 수익률 합)
def get_momentum_score(series, idx=-1):
    m1 = (series.iloc[idx] - series.iloc[idx-1]) / series.iloc[idx-1]
    m3 = (series.iloc[idx] - series.iloc[idx-3]) / series.iloc[idx-3]
    m6 = (series.iloc[idx] - series.iloc[idx-6]) / series.iloc[idx-6]
    m9 = (series.iloc[idx] - series.iloc[idx-9]) / series.iloc[idx-9]
    m12 = (series.iloc[idx] - series.iloc[idx-12]) / series.iloc[idx-12]
    return m1 + m3 + m6 + m9 + m12

# ----------------------------------------------------
# 3. 메인 화면 로직 및 UI 출력
# ----------------------------------------------------
try:
    with st.spinner('야후 파이낸스에서 두 전략의 최신 데이터를 가져오는 중입니다...'):
        data = load_financial_data(all_tickers)
        
    # 월말 데이터 추출 (오류 방지를 위해 'ME' 사용)
    month_data = data.resample('ME').last()
    
    if len(month_data) < 13:
        st.error("모멘텀 점수를 산출하기 위한 과거 데이터(최소 13개월)가 부족합니다.")
    else:
        latest_date = month_data.index[-1].strftime('%Y년 %m월 %d일')
        st.subheader(f"📅 실시간 분석 기준일: {latest_date}")
        
        # 카나리아 자산(TIP) 모멘텀
        tip_score = get_momentum_score(month_data["TIP"])
        st.metric(label="🎗️ 현재 TIP (카나리아) 모멘텀 스코어", value=f"{tip_score:.4f}")
        
        # 탭(Tab) 생성
        tab1, tab2 = st.tabs(["📌 전략 1: 오리지널 BAA", "🚀 전략 2: 섹터 중심 BAA"])
        
        # --- [탭 1: 오리지널 BAA 로직] ---
        with tab1:
            st.markdown("**(공격형: QQQ, VEU, VWO, TLT, IEF, DBC, VNQ / 방어형: IEF, BIL)**")
            col1, col2 = st.columns([1, 2])
            buy1 = {}
            
            with col1:
                if tip_score > 0:
                    st.success("📈 **시장 국면:** 공격형 매수장")
                    scores1 = {asset: get_momentum_score(month_data[asset]) for asset in strat1_off}
                    top4_1 = pd.Series(scores1).sort_values(ascending=False).nlargest(4)
                    for asset in top4_1.index: buy1[asset] = "25.0%"
                else:
                    st.warning("📉 **시장 국면:** 방어형 매수장")
                    scores1 = {asset: get_momentum_score(month_data[asset]) for asset in strat1_def}
                    top1_1 = pd.Series(scores1).sort_values(ascending=False).nlargest(1)
                    buy1[top1_1.index[0]] = "100.0%"
                    
            with col2:
                st.write("🎯 **이번 달 전략 1 목표 비중**")
                st.table(pd.DataFrame(list(buy1.items()), columns=['Ticker', '목표 비중']))
            
            # 모멘텀 전체 순위 (전략 1)
            scores1_all = {asset: get_momentum_score(month_data[asset]) for asset in (strat1_off + strat1_def)}
            df1_scores = pd.DataFrame(list(scores1_all.items()), columns=['Ticker', 'Score']).set_index('Ticker').sort_values(by='Score', ascending=False)
            with st.expander("전략 1 자산군 전체 모멘텀 순위 보기"):
                st.dataframe(df1_scores.style.format("{:.4f}"), use_container_width=True)

        # --- [탭 2: 섹터 BAA 로직] ---
        with tab2:
            st.markdown("**(공격형: IBB, IGV, SKYY, SOXX, XLE, XRT, IEF, DBC / 방어형: IEF, BIL)**")
            col3, col4 = st.columns([1, 2])
            buy2 = {}
            
            with col3:
                if tip_score > 0:
                    st.success("📈 **시장 국면:** 공격형 매수장")
                    scores2 = {asset: get_momentum_score(month_data[asset]) for asset in strat2_off}
                    top4_2 = pd.Series(scores2).sort_values(ascending=False).nlargest(4)
                    for asset in top4_2.index: buy2[asset] = "25.0%"
                else:
                    st.warning("📉 **시장 국면:** 방어형 매수장")
                    scores2 = {asset: get_momentum_score(month_data[asset]) for asset in strat2_def}
                    top1_2 = pd.Series(scores2).sort_values(ascending=False).nlargest(1)
                    buy2[top1_2.index[0]] = "100.0%"
                    
            with col4:
                st.write("🎯 **이번 달 전략 2 목표 비중**")
                st.table(pd.DataFrame(list(buy2.items()), columns=['Ticker', '목표 비중']))
                
            # 모멘텀 전체 순위 (전략 2)
            scores2_all = {asset: get_momentum_score(month_data[asset]) for asset in (strat2_off + strat2_def)}
            df2_scores = pd.DataFrame(list(scores2_all.items()), columns=['Ticker', 'Score']).set_index('Ticker').sort_values(by='Score', ascending=False)
            with st.expander("전략 2 자산군 전체 모멘텀 순위 보기"):
                st.dataframe(df2_scores.style.format("{:.4f}"), use_container_width=True)

except Exception as e:
    st.error(f"데이터 로드 및 계산 중 오류가 발생했습니다. 오류 내용: {e}")
