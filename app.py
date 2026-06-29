import streamlit as st
import pandas as pd
import numpy as np
import datetime
import yfinance as yf
import pandas_datareader.data as web

# 페이지 기본 설정
st.set_page_config(page_title="통합 동적 자산배분 대시보드", layout="wide")

st.title("📊 통합 동적 자산배분 실시간 리밸런싱 대시보드")
st.markdown("매월 말 각 전략의 알고리즘과 거시경제 지표를 분석하여 실시간 최적의 투자 비중을 안내합니다.")

# ----------------------------------------------------
# 1. 자산군 및 이름 매핑 정의
# ----------------------------------------------------
# 전략 1: 밸런스 전략
strat1_off = ["QQQ", "VEU", "VWO", "TLT", "IEF", "DBC", "VNQ"]
strat1_def = ["IEF", "BIL"]

# 전략 2: 미국밸런스 섹터 전략
strat2_off = ["IBB", "IGV", "SKYY", "SOXX", "XLE", "XRT", "IEF", "DBC"]
strat2_def = ["IEF", "BIL"]

# 전략 3: LAA 전략
laa_assets = ["IWD", "GLD", "IEF", "QQQ", "SHY", "SPY"]

# 전략 4: 한국형가속자산배분전략 (지정된 6종목 구성)
strat4_off = ["251350.KS", "133690.KS"]
strat4_def = ["153130.KS", "130680.KS", "308620.KS", "132030.KS"]

# 한글 이름 매핑 사전
asset_names = {
    "251350.KS": "KODEX 선진국MSCI World",
    "133690.KS": "TIGER 미국나스닥100",
    "153130.KS": "KODEX 단기채권",
    "130680.KS": "TIGER 단기통안채",
    "308620.KS": "KODEX 미국채10년선물",
    "132030.KS": "KODEX 단기채권PLUS",
    "QQQ": "Invesco QQQ (미국 나스닥)",
    "SPY": "SPDR S&P 500 ETF",
    "IEF": "iShares 7-10 Year Treasury Bond",
    "BIL": "SPDR Bloomberg 1-3 Month T-Bill",
    "SHY": "iShares 1-3 Year Treasury Bond",
    "GLD": "SPDR Gold Shares (금)",
    "IWD": "iShares Russell 1000 Value ETF"
}

# 중복 제거한 전체 티커 리스트 수집
all_tickers = list(set(strat1_off + strat1_def + strat2_off + strat2_def + laa_assets + strat4_off + strat4_def + ["TIP"]))

# ----------------------------------------------------
# 2. 데이터 로드 및 전처리
# ----------------------------------------------------
@st.cache_data(ttl=14400) # 4시간 데이터 캐싱
def load_financial_data(tickers):
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

# BAA용 모멘텀 스코어 (1, 3, 6, 9, 12개월 수익률 합)
def get_baa_score(series, idx=-1):
    m1 = (series.iloc[idx] - series.iloc[idx-1]) / series.iloc[idx-1]
    m3 = (series.iloc[idx] - series.iloc[idx-3]) / series.iloc[idx-3]
    m6 = (series.iloc[idx] - series.iloc[idx-6]) / series.iloc[idx-6]
    m9 = (series.iloc[idx] - series.iloc[idx-9]) / series.iloc[idx-9]
    m12 = (series.iloc[idx] - series.iloc[idx-12]) / series.iloc[idx-12]
    return m1 + m3 + m6 + m9 + m12

# AAA(가속)용 모멘텀 스코어 (1, 3, 6개월 수익률 합)
def get_aaa_score(series, idx=-1):
    m1 = (series.iloc[idx] - series.iloc[idx-1]) / series.iloc[idx-1]
    m3 = (series.iloc[idx] - series.iloc[idx-3]) / series.iloc[idx-3]
    m6 = (series.iloc[idx] - series.iloc[idx-6]) / series.iloc[idx-6]
    return m1 + m3 + m6

# ----------------------------------------------------
# 3. 메인 화면 연산 및 UI 렌더링
# ----------------------------------------------------
try:
    with st.spinner('금융 시장 및 미 연준 거시경제 데이터를 실시간 동기화 중입니다...'):
        data = load_financial_data(all_tickers)
        unrate_data = load_fred_data()
        
    month_data = data.resample('ME').last()
    
    if len(month_data) < 13:
        st.error("모멘텀 산출에 필요한 최소 역사적 데이터(13개월)가 부족합니다.")
    else:
        latest_date = month_data.index[-1].strftime('%Y년 %m월 %d일')
        st.subheader(f"📅 실시간 데이터 기준일: {latest_date}")
        
        # 4개의 탭 구성 (요청하신 명칭 수정 반영)
        tab1, tab2, tab3, tab4 = st.tabs([
            "📌 1. 밸런스 전략", 
            "🚀 2. 미국밸런스 섹터 전략", 
            "🛡️ 3. LAA 전략", 
            "⚡ 4. 한국형가속자산배분전략"
        ])
        
        # 카나리아 자산 스코어 계산 (전략 1, 2 공통 적용)
        tip_score = get_baa_score(month_data["TIP"])
        
        # --- [탭 1: 1. 밸런스 전략] ---
        with tab1:
            st.markdown("**(공격: QQQ, VEU, VWO, TLT, IEF, DBC, VNQ / 수비: IEF, BIL)**")
            col1, col2 = st.columns([1, 2])
            buy1 = {}
            with col1:
                st.metric(label="🎗️ TIP 카나리아 스코어", value=f"{tip_score:.4f}")
                if tip_score > 0:
                    st.success("📈 **시장 국면:** 공격형 자산 매수장")
                    scores1 = {asset: get_baa_score(month_data[asset]) for asset in strat1_off}
                    top4_1 = pd.Series(scores1).sort_values(ascending=False).nlargest(4)
                    for asset in top4_1.index: buy1[asset] = "25.0%"
                else:
                    st.warning("📉 **시장 국면:** 방어형 안전자산 대피장")
                    scores1 = {asset: get_baa_score(month_data[asset]) for asset in strat1_def}
                    top1_1 = pd.Series(scores1).sort_values(ascending=False).nlargest(1)
                    buy1[top1_1.index[0]] = "100.0%"
            with col2:
                st.write("🎯 **이번 달 목표 포트폴리오 비중**")
                df_b1 = pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy1.items()])
                st.table(df_b1)

        # --- [탭 2: 2. 미국밸런스 섹터 전략] ---
        with tab2:
            st.markdown("**(공격: IBB, IGV, SKYY, SOXX, XLE, XRT, IEF, DBC / 수비: IEF, BIL)**")
            col3, col4 = st.columns([1, 2])
            buy2 = {}
            with col3:
                st.metric(label="🎗️ TIP 카나리아 스코어", value=f"{tip_score:.4f}")
                if tip_score > 0:
                    st.success("📈 **시장 국면:** 공격형 자산 매수장")
                    scores2 = {asset: get_baa_score(month_data[asset]) for asset in strat2_off}
                    top4_2 = pd.Series(scores2).sort_values(ascending=False).nlargest(4)
                    for asset in top4_2.index: buy2[asset] = "25.0%"
                else:
                    st.warning("📉 **시장 국면:** 방어형 안전자산 대피장")
                    scores2 = {asset: get_baa_score(month_data[asset]) for asset in strat2_def}
                    top1_2 = pd.Series(scores2).sort_values(ascending=False).nlargest(1)
                    buy2[top1_2.index[0]] = "100.0%"
            with col4:
                st.write("🎯 **이번 달 목표 포트폴리오 비중**")
                df_b2 = pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy2.items()])
                st.table(df_b2)

        # --- [탭 3: LAA] ---
        with tab3:
            st.markdown("**(고정자산 75%: IWD, GLD, IEF 각각 25% / 타이밍자산 25%: QQQ 또는 SHY)**")
            col5, col6 = st.columns([1, 2])
            buy3 = {"IWD": "25.0%", "GLD": "25.0%", "IEF": "25.0%"}
            
            spy_close = data['SPY']
            spy_200ma = spy_close.rolling(window=200).mean()
            current_spy = spy_close.iloc[-1]
            current_spy_200ma = spy_200ma.iloc[-1]
            cond1_bear = current_spy < current_spy_200ma
            
            unrate_data['12ma'] = unrate_data['UNRATE'].rolling(window=12).mean()
            unrate_clean = unrate_data.dropna()
            current_unrate = unrate_clean['UNRATE'].iloc[-1]
            current_unrate_12ma = unrate_clean['12ma'].iloc[-1]
            
            with col5:
                if cond1_bear: st.error(f"❌ S&P500 ({current_spy:.2f}) < 200이평선 ({current_spy_200ma:.2f})")
                else: st.success(f"▲ S&P500 ({current_spy:.2f}) >= 200이평선 ({current_spy_200ma:.2f})")
                
                if current_unrate > current_unrate_12ma: st.error(f"❌ 미국 실업률 ({current_unrate:.1f}%) > 12달 평균 ({current_unrate_12ma:.2f}%)")
                else: st.success(f"▲ 미국 실업률 ({current_unrate:.1f}%) <= 12달 평균 ({current_unrate_12ma:.2f}%)")
                
                if cond1_bear and (current_unrate > current_unrate_12ma):
                    st.warning("🚨 **시장 국면:** 동시 조건 충족 불황장 ➔ **SHY 매수**")
                    buy3["SHY"] = "25.0%"
                else:
                    st.info("☀️ **시장 국면:** 경제 평시/회복기 ➔ **QQQ 매수**")
                    buy3["QQQ"] = "25.0%"
            with col6:
                st.write("🎯 **이번 달 목표 포트폴리오 비중**")
                df_b3 = pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy3.items()])
                st.table(df_b3)

        # --- [탭 4: 한국형가속자산배분전략] ---
        with tab4:
            st.markdown("**(공격: 선진국MSCI, 나스닥100 / 수비: 단기채, 단기통안채, 미국채10년선물, 단기채PLUS)**")
            col7, col8 = st.columns([1, 2])
            buy4 = {}
            
            # 지정된 2개 공격자산의 1, 3, 6개월 모멘텀 스코어 계산
            aaa_scores = {asset: get_aaa_score(month_data[asset]) for asset in strat4_off}
            aaa_series = pd.Series(aaa_scores)
            max_score = aaa_series.max()
            
            with col7:
                st.write("📊 **공격 자산별 모멘텀 지표 (1+3+6M)**")
                df_aaa_sc = pd.DataFrame(list(aaa_scores.items()), columns=['Ticker', '모멘텀 스코어']).set_index('Ticker')
                st.dataframe(df_aaa_sc.style.format("{:.4f}"), use_container_width=True)
                
                if max_score > 0:
                    st.success(f"📈 최고 스코어({max_score:.4f}) > 0 ➔ **공격형 자산 100% 집중**")
                    top1_aaa = aaa_series.nlargest(1)
                    buy4[top1_aaa.index[0]] = "100.0%"
                else:
                    st.warning(f"📉 최고 스코어({max_score:.4f}) <= 0 ➔ **방어형 자산 대피 (최근 1달 우수 자산)**")
                    # 지정된 4개 방어자산 평가
                    def_momentum = {}
                    for asset in strat4_def:
                        def_momentum[asset] = month_data[asset].iloc[-1] / month_data[asset].iloc[-2]
                    
                    def_series = pd.Series(def_momentum)
                    top1_def = def_series.nlargest(1)
                    buy4[top1_def.index[0]] = "100.0%"
            
            with col8:
                st.write("🎯 **이번 달 목표 포트폴리오 비중**")
                df_b4 = pd.DataFrame([{"Ticker": k, "자산명": asset_names.get(k, k), "비중": v} for k, v in buy4.items()])
                st.table(df_b4)

except Exception as e:
    st.error(f"데이터 연산 가공 중 예측하지 못한 오류가 발생했습니다: {e}")
