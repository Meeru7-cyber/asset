import streamlit as st
import pandas as pd
import numpy as np
import datetime
import yfinance as yf
import pandas_datareader.data as web

# 페이지 기본 설정
st.set_page_config(page_title="동적 자산배분(BAA/LAA) 대시보드", layout="wide")

st.title("📊 통합 자산배분 실시간 리밸런싱 대시보드")
st.markdown("매월 말 각 전략의 알고리즘과 거시경제 지표를 분석하여 최적의 투자 비중을 계산합니다.")

# ----------------------------------------------------
# 1. 자산군 정의
# ----------------------------------------------------
# BAA 전략 1: 오리지널
strat1_off = ["QQQ", "VEU", "VWO", "TLT", "IEF", "DBC", "VNQ"]
strat1_def = ["IEF", "BIL"]

# BAA 전략 2: 섹터 중심
strat2_off = ["IBB", "IGV", "SKYY", "SOXX", "XLE", "XRT", "IEF", "DBC"]
strat2_def = ["IEF", "BIL"]

# LAA 전략 3
laa_assets = ["IWD", "GLD", "IEF", "QQQ", "SHY", "SPY"]

# 중복을 제거한 전체 티커 리스트
all_tickers = list(set(strat1_off + strat1_def + strat2_off + strat2_def + laa_assets + ["TIP"]))

# ----------------------------------------------------
# 2. 데이터 로드 및 전처리
# ----------------------------------------------------
@st.cache_data(ttl=14400) # 4시간 캐싱
def load_financial_data(tickers):
    # 200일 이동평균선 등을 계산하기 위해 넉넉히 2년치(730일) 데이터 수집
    start_date = (datetime.date.today() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    df = yf.download(tickers, start=start_date, end=end_date)
    if 'Close' in df.columns:
        df = df['Close']
    df = df.dropna()
    return df

@st.cache_data(ttl=14400)
def load_fred_data():
    start_date = (datetime.date.today() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')
    unrate = web.DataReader("UNRATE", "fred", start_date)
    return unrate

# BAA 모멘텀 스코어 계산 함수
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
    with st.spinner('야후 파이낸스 및 FRED(미 연준)에서 최신 데이터를 가져오는 중입니다...'):
        data = load_financial_data(all_tickers)
        unrate_data = load_fred_data()
        
    # 월말 데이터 추출 (BAA 모멘텀용)
    month_data = data.resample('ME').last()
    
    if len(month_data) < 13:
        st.error("모멘텀 점수를 산출하기 위한 과거 데이터(최소 13개월)가 부족합니다.")
    else:
        latest_date = month_data.index[-1].strftime('%Y년 %m월 %d일')
        st.subheader(f"📅 실시간 분석 기준일: {latest_date}")
        
        # 탭(Tab) 3개 생성
        tab1, tab2, tab3 = st.tabs(["📌 1. 오리지널 BAA", "🚀 2. 섹터 중심 BAA", "🛡️ 3. LAA 전략"])
        
        # 카나리아 자산(TIP) 모멘텀 (BAA 공통)
        tip_score = get_momentum_score(month_data["TIP"])
        
        # --- [탭 1: 오리지널 BAA 로직] ---
        with tab1:
            st.markdown("**(공격형: QQQ, VEU, VWO, TLT, IEF, DBC, VNQ / 방어형: IEF, BIL)**")
            col1, col2 = st.columns([1, 2])
            buy1 = {}
            
            with col1:
                st.metric(label="🎗️ 현재 TIP 스코어", value=f"{tip_score:.4f}")
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
                st.write("🎯 **이번 달 오리지널 BAA 목표 비중**")
                st.table(pd.DataFrame(list(buy1.items()), columns=['Ticker', '목표 비중']))

        # --- [탭 2: 섹터 BAA 로직] ---
        with tab2:
            st.markdown("**(공격형: IBB, IGV, SKYY, SOXX, XLE, XRT, IEF, DBC / 방어형: IEF, BIL)**")
            col3, col4 = st.columns([1, 2])
            buy2 = {}
            
            with col3:
                st.metric(label="🎗️ 현재 TIP 스코어", value=f"{tip_score:.4f}")
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
                st.write("🎯 **이번 달 섹터 BAA 목표 비중**")
                st.table(pd.DataFrame(list(buy2.items()), columns=['Ticker', '목표 비중']))

        # --- [탭 3: LAA 로직] ---
        with tab3:
            st.markdown("**(고정자산: IWD, GLD, IEF / 타이밍자산: QQQ or SHY)**")
            col5, col6 = st.columns([1, 2])
            buy3 = {"IWD": "25.0%", "GLD": "25.0%", "IEF": "25.0%"}
            
            # LAA 지표 계산
            spy_close = data['SPY']
            spy_200ma = spy_close.rolling(window=200).mean()
            current_spy = spy_close.iloc[-1]
            current_spy_200ma = spy_200ma.iloc[-1]
            cond1_bearish = current_spy < current_spy_200ma
            
            unrate_data['12ma'] = unrate_data['UNRATE'].rolling(window=12).mean()
            unrate_clean = unrate_data.dropna()
            current_unrate = unrate_clean['UNRATE'].iloc[-1]
            current_unrate_12ma = unrate_clean['12ma'].iloc[-1]
            cond2_bearish = current_unrate > current_unrate_12ma
            
            is_laa_bearish = cond1_bearish and cond2_bearish
            
            with col5:
                # 조건 1 현황 출력
                if cond1_bearish:
                    st.error(f"📉 S&P500 ({current_spy:.2f}) < 200MA ({current_spy_200ma:.2f})")
                else:
                    st.success(f"📈 S&P500 ({current_spy:.2f}) >= 200MA ({current_spy_200ma:.2f})")
                
                # 조건 2 현황 출력
                if cond2_bearish:
                    st.error(f"📉 실업률 ({current_unrate:.1f}%) > 12MA ({current_unrate_12ma:.2f}%)")
                else:
                    st.success(f"📈 실업률 ({current_unrate:.1f}%) <= 12MA ({current_unrate_12ma:.2f}%)")
                
                st.divider()
                
                # 최종 판단
                if is_laa_bearish:
                    st.warning("🚨 **시장 국면:** 불황장 (Bearish & Depression) ➔ 타이밍 자산: **SHY**")
                    buy3["SHY"] = "25.0%"
                else:
                    st.info("☀️ **시장 국면:** 평시 ➔ 타이밍 자산: **QQQ**")
                    buy3["QQQ"] = "25.0%"
            
            with col6:
                st.write("🎯 **이번 달 LAA 목표 비중**")
                # DataFrame 변환 후 인덱스를 재설정하여 깔끔하게 출력
                df_buy3 = pd.DataFrame(list(buy3.items()), columns=['Ticker', '목표 비중'])
                df_buy3.index = np.arange(1, len(df_buy3) + 1)
                st.table(df_buy3)

except Exception as e:
    st.error(f"데이터 로드 및 계산 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. 오류 내용: {e}")
