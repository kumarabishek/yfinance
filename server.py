"""
Yahoo Finance MCP Server — Remote (Streamable HTTP)
Built with FastMCP + yfinance for use across Claude iOS, web, and desktop.

Usage:
  Local:  uv run server.py
  CLI:    fastmcp run server.py --transport streamable-http --port 8000
"""

import os
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
import yfinance as yf
import json
from datetime import datetime, timedelta

mcp = FastMCP(
    "Yahoo Finance",
    json_response=True,
    stateless_http=True,
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


# ──────────────────────────────────────────────
# TOOL 1: Stock Quote & Key Metrics
# ──────────────────────────────────────────────
@mcp.tool()
def get_stock_quote(ticker: str) -> dict:
    """
    Get current stock quote with key metrics including price, change,
    market cap, P/E, EPS, 52-week range, volume, beta, and sector info.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        if not info or "regularMarketPrice" not in info:
            return {"error": f"Ticker '{ticker}' not found or no data available."}

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        change = round(price - prev_close, 2) if price and prev_close else None
        change_pct = round((change / prev_close) * 100, 2) if change and prev_close else None

        return {
            "ticker": ticker.upper(),
            "name": info.get("shortName") or info.get("longName"),
            "price": price,
            "change": change,
            "change_percent": change_pct,
            "currency": info.get("currency"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "pe_trailing": info.get("trailingPE"),
            "pe_forward": info.get("forwardPE"),
            "eps_trailing": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "50d_avg": info.get("fiftyDayAverage"),
            "200d_avg": info.get("twoHundredDayAverage"),
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
            "dividend_yield": info.get("dividendYield"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "analyst_target_mean": info.get("targetMeanPrice"),
            "analyst_target_low": info.get("targetLowPrice"),
            "analyst_target_high": info.get("targetHighPrice"),
            "analyst_recommendation": info.get("recommendationKey"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 2: Historical Prices
# ──────────────────────────────────────────────
@mcp.tool()
def get_historical_prices(
    ticker: str,
    period: str = "3mo",
    interval: str = "1d",
) -> dict:
    """
    Get historical OHLCV price data.

    Args:
        ticker: Stock ticker symbol
        period: Data period - 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        interval: Data interval - 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
    """
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period, interval=interval)

        if hist.empty:
            return {"error": f"No historical data for '{ticker}'."}

        records = []
        for date, row in hist.iterrows():
            records.append({
                "date": date.strftime("%Y-%m-%d %H:%M:%S") if interval in ["1m","2m","5m","15m","30m","60m","90m","1h"] else date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            })

        return {
            "ticker": ticker.upper(),
            "period": period,
            "interval": interval,
            "data_points": len(records),
            "prices": records,
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 3: Financial Statements
# ──────────────────────────────────────────────
@mcp.tool()
def get_financials(
    ticker: str,
    statement: str = "income",
    quarterly: bool = False,
) -> dict:
    """
    Get financial statements.

    Args:
        ticker: Stock ticker symbol
        statement: Type - 'income', 'balance', or 'cashflow'
        quarterly: If True, return quarterly data; otherwise annual
    """
    try:
        stock = yf.Ticker(ticker.upper())

        if statement == "income":
            df = stock.quarterly_financials if quarterly else stock.financials
        elif statement == "balance":
            df = stock.quarterly_balance_sheet if quarterly else stock.balance_sheet
        elif statement == "cashflow":
            df = stock.quarterly_cashflow if quarterly else stock.cashflow
        else:
            return {"error": "statement must be 'income', 'balance', or 'cashflow'"}

        if df is None or df.empty:
            return {"error": f"No {statement} data for '{ticker}'."}

        result = {}
        for col in df.columns:
            period_key = col.strftime("%Y-%m-%d")
            result[period_key] = {}
            for idx in df.index:
                val = df.loc[idx, col]
                if val is not None and str(val) != "nan":
                    result[period_key][str(idx)] = float(val)

        return {
            "ticker": ticker.upper(),
            "statement": statement,
            "frequency": "quarterly" if quarterly else "annual",
            "data": result,
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 4: Analyst Recommendations
# ──────────────────────────────────────────────
@mcp.tool()
def get_analyst_recommendations(ticker: str) -> dict:
    """
    Get recent analyst recommendations, upgrades, and downgrades.
    """
    try:
        stock = yf.Ticker(ticker.upper())
        recs = stock.recommendations

        if recs is None or recs.empty:
            return {"error": f"No analyst recommendations for '{ticker}'."}

        recent = recs.tail(20)
        items = []
        for _, row in recent.iterrows():
            items.append({
                "firm": row.get("Firm") or str(row.get("firm", "")),
                "grade": row.get("To Grade") or row.get("toGrade", ""),
                "from_grade": row.get("From Grade") or row.get("fromGrade", ""),
                "action": row.get("Action") or row.get("action", ""),
            })

        return {"ticker": ticker.upper(), "recommendations": items}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 5: Options Chain
# ──────────────────────────────────────────────
@mcp.tool()
def get_options(
    ticker: str,
    expiration: str = "",
    option_type: str = "calls",
) -> dict:
    """
    Get options chain data.

    Args:
        ticker: Stock ticker symbol
        expiration: Expiration date (YYYY-MM-DD). Empty = nearest expiration.
        option_type: 'calls' or 'puts'
    """
    try:
        stock = yf.Ticker(ticker.upper())
        expirations = stock.options

        if not expirations:
            return {"error": f"No options data for '{ticker}'."}

        exp = expiration if expiration else expirations[0]
        chain = stock.option_chain(exp)
        df = chain.calls if option_type == "calls" else chain.puts

        options = []
        for _, row in df.iterrows():
            options.append({
                "strike": row.get("strike"),
                "last_price": row.get("lastPrice"),
                "bid": row.get("bid"),
                "ask": row.get("ask"),
                "volume": row.get("volume"),
                "open_interest": row.get("openInterest"),
                "implied_vol": row.get("impliedVolatility"),
                "in_the_money": row.get("inTheMoney"),
            })

        return {
            "ticker": ticker.upper(),
            "expiration": exp,
            "available_expirations": list(expirations),
            "type": option_type,
            "options": options,
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 6: Stock News
# ──────────────────────────────────────────────
@mcp.tool()
def get_stock_news(ticker: str) -> dict:
    """Get recent news articles for a stock ticker."""
    try:
        stock = yf.Ticker(ticker.upper())
        news = stock.news

        if not news:
            return {"error": f"No news for '{ticker}'."}

        articles = []
        for item in news[:10]:
            content = item.get("content", {})
            articles.append({
                "title": content.get("title") or item.get("title"),
                "publisher": content.get("provider", {}).get("displayName")
                    or item.get("publisher"),
                "link": content.get("canonicalUrl", {}).get("url")
                    or item.get("link"),
                "published": content.get("pubDate")
                    or item.get("providerPublishTime"),
            })

        return {"ticker": ticker.upper(), "articles": articles}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 7: Compare Stocks
# ──────────────────────────────────────────────
@mcp.tool()
def compare_stocks(tickers: str) -> dict:
    """
    Side-by-side comparison of multiple stocks.

    Args:
        tickers: Comma-separated list of ticker symbols (e.g., "COHR,LITE,AAOI,AXTI")
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        results = []

        for t in ticker_list:
            stock = yf.Ticker(t)
            info = stock.info
            if not info:
                results.append({"ticker": t, "error": "No data"})
                continue

            price = info.get("regularMarketPrice") or info.get("currentPrice")
            results.append({
                "ticker": t,
                "name": info.get("shortName"),
                "price": price,
                "market_cap": info.get("marketCap"),
                "pe_trailing": info.get("trailingPE"),
                "pe_forward": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "eps_trailing": info.get("trailingEps"),
                "eps_forward": info.get("forwardEps"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "profit_margin": info.get("profitMargins"),
                "beta": info.get("beta"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "analyst_target": info.get("targetMeanPrice"),
                "recommendation": info.get("recommendationKey"),
            })

        return {"comparison": results}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 8: Earnings
# ──────────────────────────────────────────────
@mcp.tool()
def get_earnings(ticker: str) -> dict:
    """Get earnings history, EPS surprises, and upcoming earnings dates."""
    try:
        stock = yf.Ticker(ticker.upper())

        # Earnings history
        earnings_hist = stock.earnings_history
        history = []
        if earnings_hist is not None and not earnings_hist.empty:
            for _, row in earnings_hist.iterrows():
                history.append({
                    "quarter": str(row.get("quarter", "")),
                    "eps_estimate": row.get("epsEstimate"),
                    "eps_actual": row.get("epsActual"),
                    "surprise_pct": row.get("surprisePercent"),
                })

        # Upcoming earnings
        cal = stock.calendar
        earnings_date = None
        if cal is not None:
            if isinstance(cal, dict):
                ed = cal.get("Earnings Date")
                if ed:
                    earnings_date = str(ed[0]) if isinstance(ed, list) else str(ed)

        return {
            "ticker": ticker.upper(),
            "earnings_history": history,
            "next_earnings_date": earnings_date,
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 9: Holders
# ──────────────────────────────────────────────
@mcp.tool()
def get_holders(ticker: str) -> dict:
    """Get institutional holders, mutual fund holders, and insider transactions."""
    try:
        stock = yf.Ticker(ticker.upper())

        inst_holders = []
        if stock.institutional_holders is not None:
            for _, row in stock.institutional_holders.head(15).iterrows():
                inst_holders.append({
                    "holder": row.get("Holder"),
                    "shares": row.get("Shares"),
                    "value": row.get("Value"),
                    "pct_held": row.get("pctHeld") or row.get("% Out"),
                })

        insider_txns = []
        if stock.insider_transactions is not None:
            for _, row in stock.insider_transactions.head(10).iterrows():
                insider_txns.append({
                    "insider": row.get("Insider") or row.get("insider"),
                    "relation": row.get("Relation") or row.get("relation"),
                    "transaction": row.get("Transaction") or row.get("transaction"),
                    "shares": row.get("Shares") or row.get("shares"),
                    "value": row.get("Value") or row.get("value"),
                })

        return {
            "ticker": ticker.upper(),
            "institutional_holders": inst_holders,
            "insider_transactions": insider_txns,
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 10: Search Ticker
# ──────────────────────────────────────────────
@mcp.tool()
def search_ticker(query: str) -> dict:
    """
    Search for tickers by company name or partial symbol.

    Args:
        query: Company name or partial ticker to search for
    """
    try:
        from yfinance import Search
        results = Search(query)

        quotes = []
        if hasattr(results, "quotes") and results.quotes:
            for q in results.quotes[:10]:
                quotes.append({
                    "symbol": q.get("symbol"),
                    "name": q.get("shortname") or q.get("longname"),
                    "exchange": q.get("exchange"),
                    "type": q.get("quoteType"),
                })

        news = []
        if hasattr(results, "news") and results.news:
            for n in results.news[:5]:
                news.append({
                    "title": n.get("title"),
                    "publisher": n.get("publisher"),
                    "link": n.get("link"),
                })

        return {"query": query, "quotes": quotes, "news": news}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 11: Technical Indicator Signals (upgraded via ta library)
# ──────────────────────────────────────────────
@mcp.tool()
def get_technical_signals(ticker: str) -> dict:
    """
    Compute RSI, MACD, Bollinger Bands, ATR, Stochastic, and OBV from recent price history.
    Returns current indicator values and buy/sell/neutral interpretations.
    """
    try:
        import ta

        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period="6mo", interval="1d")

        if hist.empty or len(hist) < 30:
            return {"error": "Not enough historical data to compute indicators."}

        close = hist["Close"]
        high = hist["High"]
        low = hist["Low"]
        volume = hist["Volume"]
        current_price = float(close.iloc[-1])

        # RSI (14-day)
        rsi_val = round(float(ta.momentum.RSIIndicator(close=close, window=14).rsi().iloc[-1]), 2)
        rsi_signal = "overbought" if rsi_val > 70 else "oversold" if rsi_val < 30 else "neutral"

        # MACD (12, 26, 9)
        macd = ta.trend.MACD(close=close)
        macd_hist_val = float(macd.macd_diff().iloc[-1])
        macd_direction = "bullish" if macd_hist_val > 0 else "bearish"

        # Bollinger Bands (20-day, 2 std)
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bb_upper = float(bb.bollinger_hband().iloc[-1])
        bb_lower = float(bb.bollinger_lband().iloc[-1])
        bb_range = bb_upper - bb_lower
        bb_position = (current_price - bb_lower) / bb_range if bb_range > 0 else 0.5
        bb_signal = "overbought" if bb_position > 0.8 else "oversold" if bb_position < 0.2 else "neutral"

        # ATR — measures volatility in price units
        atr_val = round(float(ta.volatility.AverageTrueRange(high=high, low=low, close=close).average_true_range().iloc[-1]), 4)

        # Stochastic (14, 3)
        stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close)
        stoch_k = round(float(stoch.stoch().iloc[-1]), 2)
        stoch_d = round(float(stoch.stoch_signal().iloc[-1]), 2)
        stoch_signal = "overbought" if stoch_k > 80 else "oversold" if stoch_k < 20 else "neutral"

        # OBV — volume trend confirmation
        obv_series = ta.volume.OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
        obv_trend = "bullish" if float(obv_series.iloc[-1]) > float(obv_series.iloc[-5]) else "bearish"

        return {
            "ticker": ticker.upper(),
            "price": round(current_price, 2),
            "rsi": {
                "value": rsi_val,
                "signal": rsi_signal,
                "interpretation": ">70 overbought, <30 oversold",
            },
            "macd": {
                "macd_line": round(float(macd.macd().iloc[-1]), 4),
                "signal_line": round(float(macd.macd_signal().iloc[-1]), 4),
                "histogram": round(macd_hist_val, 4),
                "direction": macd_direction,
            },
            "bollinger_bands": {
                "upper": round(bb_upper, 2),
                "middle": round(float(bb.bollinger_mavg().iloc[-1]), 2),
                "lower": round(bb_lower, 2),
                "position_pct": round(bb_position * 100, 1),
                "signal": bb_signal,
            },
            "atr": {
                "value": atr_val,
                "interpretation": "Average daily price range — higher = more volatile",
            },
            "stochastic": {
                "k": stoch_k,
                "d": stoch_d,
                "signal": stoch_signal,
                "interpretation": ">80 overbought, <20 oversold",
            },
            "obv": {
                "trend": obv_trend,
                "interpretation": "Bullish = volume confirming price rise; Bearish = divergence",
            },
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 12: Linear Trend Extrapolation
# ──────────────────────────────────────────────
@mcp.tool()
def get_price_trend_forecast(
    ticker: str,
    days_back: int = 30,
) -> dict:
    """
    Fit a linear trend to recent closing prices and extrapolate forward.
    Returns projected prices at 7, 14, and 30 days, plus trend slope and R².

    Args:
        ticker: Stock ticker symbol
        days_back: Number of recent trading days to fit the trend on (default 30)
    """
    try:
        import numpy as np

        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period="6mo", interval="1d")

        if hist.empty or len(hist) < days_back:
            return {"error": f"Not enough data — need at least {days_back} trading days."}

        close = hist["Close"].tail(days_back).values
        x = np.arange(len(close))

        # Linear fit
        coeffs = np.polyfit(x, close, 1)
        slope = float(coeffs[0])
        y_pred = np.polyval(coeffs, x)

        # R² — how well the line fits
        ss_res = float(np.sum((close - y_pred) ** 2))
        ss_tot = float(np.sum((close - np.mean(close)) ** 2))
        r_squared = round(1 - ss_res / ss_tot, 4) if ss_tot > 0 else 0.0

        current_price = float(close[-1])
        base_idx = len(close) - 1

        forecasts = {
            "7d": round(float(np.polyval(coeffs, base_idx + 7)), 2),
            "14d": round(float(np.polyval(coeffs, base_idx + 14)), 2),
            "30d": round(float(np.polyval(coeffs, base_idx + 30)), 2),
        }

        return {
            "ticker": ticker.upper(),
            "current_price": round(current_price, 2),
            "trend": "uptrend" if slope > 0 else "downtrend",
            "daily_slope": round(slope, 4),
            "r_squared": r_squared,
            "r_squared_note": "1.0 = perfect fit, <0.5 = low confidence",
            "forecast": forecasts,
            "days_used_for_fit": days_back,
            "note": "Linear extrapolation only. Assumes current trend continues — use alongside other signals.",
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 13: ML Direction Classifier
# ──────────────────────────────────────────────
@mcp.tool()
def predict_price_direction(ticker: str) -> dict:
    """
    Train a logistic regression on 1 year of technical features to predict
    whether the stock will close higher or lower tomorrow.

    Features: RSI, MACD histogram, price vs SMA20/SMA50, 5d/10d momentum, volume change.
    Validated on the last 20 trading days before predicting today.
    """
    try:
        import numpy as np
        import pandas as pd
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period="1y", interval="1d")

        if len(hist) < 80:
            return {"error": "Need at least 80 days of history to train the model."}

        close = hist["Close"]
        volume = hist["Volume"]

        # Feature engineering
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()

        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()

        features = pd.DataFrame({
            "rsi": rsi,
            "macd_hist": macd_hist,
            "price_vs_sma20": close / sma20 - 1,
            "price_vs_sma50": close / sma50 - 1,
            "momentum_5d": close.pct_change(5),
            "momentum_10d": close.pct_change(10),
            "volume_change": volume.pct_change(5),
        })

        # Target: did price go up next day?
        target = (close.shift(-1) > close).astype(int)

        df = features.copy()
        df["target"] = target
        df = df.dropna().iloc[:-1]  # drop last row (no next-day label yet)

        if len(df) < 50:
            return {"error": "Insufficient data after feature engineering."}

        X = df.drop("target", axis=1).values
        y = df["target"].values

        # Train / validate split — last 20 days as holdout
        split = len(X) - 20
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_val_s = scaler.transform(X_val)

        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_train_s, y_train)

        val_accuracy = round(float(model.score(X_val_s, y_val)), 3)

        # Predict using today's features (last row of full features df)
        today = features.dropna().iloc[-1:].values
        today_s = scaler.transform(today)
        probs = model.predict_proba(today_s)[0]

        prob_up = round(float(probs[1]) * 100, 1)
        prob_down = round(float(probs[0]) * 100, 1)
        prediction = "up" if prob_up > 50 else "down"
        confidence = max(prob_up, prob_down)

        return {
            "ticker": ticker.upper(),
            "prediction": prediction,
            "confidence_pct": confidence,
            "prob_up": prob_up,
            "prob_down": prob_down,
            "model_validation_accuracy": val_accuracy,
            "validation_window": "last 20 trading days",
            "features": ["rsi", "macd_histogram", "price_vs_sma20", "price_vs_sma50", "momentum_5d", "momentum_10d", "volume_change_5d"],
            "note": "Logistic regression on technical indicators. Not financial advice.",
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 14: Market Movers
# ──────────────────────────────────────────────
@mcp.tool()
def get_market_movers(category: str = "gainers") -> dict:
    """
    Get today's top market movers from US equities.

    Args:
        category: 'gainers', 'losers', or 'active' (most active by volume)
    """
    try:
        predefined_map = {
            "gainers": "day_gainers",
            "losers": "day_losers",
            "active": "most_actives",
        }
        key = predefined_map.get(category.lower())
        if not key:
            return {"error": "category must be 'gainers', 'losers', or 'active'"}

        response = yf.screen(key, count=15)
        quotes = response.get("quotes", [])

        results = []
        for q in quotes[:15]:
            results.append({
                "ticker": q.get("symbol"),
                "name": q.get("shortName") or q.get("longName"),
                "price": q.get("regularMarketPrice"),
                "change": round(q.get("regularMarketChange", 0), 2),
                "change_pct": round(q.get("regularMarketChangePercent", 0), 2),
                "volume": q.get("regularMarketVolume"),
                "market_cap": q.get("marketCap"),
            })

        return {"category": category, "movers": results}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 15: Sector Performance
# ──────────────────────────────────────────────
@mcp.tool()
def get_sector_performance() -> dict:
    """
    Get today's performance across all 11 S&P 500 sectors using SPDR sector ETFs.
    Shows 1-day, 5-day, and 1-month returns per sector.
    """
    try:
        sector_etfs = {
            "Technology": "XLK",
            "Financials": "XLF",
            "Healthcare": "XLV",
            "Energy": "XLE",
            "Industrials": "XLI",
            "Consumer Discretionary": "XLY",
            "Consumer Staples": "XLP",
            "Communication Services": "XLC",
            "Real Estate": "XLRE",
            "Utilities": "XLU",
            "Materials": "XLB",
        }

        tickers = list(sector_etfs.values())
        data = yf.download(tickers, period="1mo", interval="1d", progress=False, auto_adjust=True)
        close = data["Close"]

        results = []
        for sector, etf in sector_etfs.items():
            if etf not in close.columns:
                continue
            prices = close[etf].dropna()
            if len(prices) < 2:
                continue

            day_ret = round((float(prices.iloc[-1]) / float(prices.iloc[-2]) - 1) * 100, 2)
            week_ret = round((float(prices.iloc[-1]) / float(prices.iloc[-5]) - 1) * 100, 2) if len(prices) >= 5 else None
            month_ret = round((float(prices.iloc[-1]) / float(prices.iloc[0]) - 1) * 100, 2)

            results.append({
                "sector": sector,
                "etf": etf,
                "price": round(float(prices.iloc[-1]), 2),
                "return_1d_pct": day_ret,
                "return_5d_pct": week_ret,
                "return_1mo_pct": month_ret,
            })

        results.sort(key=lambda x: x["return_1d_pct"], reverse=True)
        return {"sectors": results}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 16: SEC Filings
# ──────────────────────────────────────────────
@mcp.tool()
def get_sec_filings(ticker: str) -> dict:
    """
    Get recent SEC filings for a company — 10-K (annual), 10-Q (quarterly), and 8-K (events).
    Data sourced from SEC EDGAR via edgartools (free, no API key).
    """
    try:
        from edgar import Company, set_identity
        set_identity("yfinance-mcp-bot contact@yfinance-mcp.app")

        company = Company(ticker.upper())

        def format_filings(filings, n: int = 5) -> list:
            out = []
            try:
                result = filings.latest(n) if hasattr(filings, "latest") else filings
                # edgartools returns a single object when only 1 filing exists
                items = result if hasattr(result, "__iter__") and not hasattr(result, "accession_no") else [result]
                for f in list(items)[:n]:
                    out.append({
                        "form": getattr(f, "form", None),
                        "filed": str(getattr(f, "filing_date", "") or getattr(f, "date", "")),
                        "description": getattr(f, "description", None) or getattr(f, "primaryDocument", None),
                        "url": getattr(f, "filing_index", None) or getattr(f, "document_url", None) or getattr(f, "url", None),
                    })
            except Exception:
                pass
            return out

        annual = format_filings(company.get_filings(form="10-K"), 3)
        quarterly = format_filings(company.get_filings(form="10-Q"), 4)
        events = format_filings(company.get_filings(form="8-K"), 5)

        return {
            "ticker": ticker.upper(),
            "annual_10k": annual,
            "quarterly_10q": quarterly,
            "material_events_8k": events,
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# TOOL 17: Insider Trades (SEC Form 4)
# ──────────────────────────────────────────────
@mcp.tool()
def get_insider_trades(ticker: str) -> dict:
    """
    Get recent insider trades (SEC Form 4 filings) — who bought or sold, how much, and when.
    Data sourced from SEC EDGAR via edgartools (free, no API key).
    """
    try:
        from edgar import Company, set_identity
        set_identity("yfinance-mcp-bot contact@yfinance-mcp.app")

        company = Company(ticker.upper())
        filings = company.get_filings(form="4")

        trades = []
        try:
            result = filings.latest(15) if hasattr(filings, "latest") else filings
            items = result if hasattr(result, "__iter__") and not hasattr(result, "accession_no") else [result]
            for f in list(items)[:15]:
                trades.append({
                    "filed": str(getattr(f, "filing_date", "") or getattr(f, "date", "")),
                    "form": getattr(f, "form", "4"),
                    "accession": getattr(f, "accession_no", None) or getattr(f, "accession", None),
                    "sec_url": getattr(f, "filing_index", None) or getattr(f, "document_url", None) or getattr(f, "url", None),
                })
        except Exception:
            pass

        return {
            "ticker": ticker.upper(),
            "insider_trades": trades,
            "source": "SEC EDGAR Form 4",
            "note": "For insider names and transaction amounts use get_holders. These links go directly to the raw SEC filings.",
        }
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# Run server
# ──────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="streamable-http")