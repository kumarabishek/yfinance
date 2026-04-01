"""
Yahoo Finance MCP Server — Remote (Streamable HTTP)
Built with FastMCP + yfinance for use across Claude iOS, web, and desktop.

Usage:
  Local:  uv run server.py
  CLI:    fastmcp run server.py --transport streamable-http --port 8000
"""

import os
from mcp.server.fastmcp import FastMCP
import yfinance as yf
import json
from datetime import datetime, timedelta

mcp = FastMCP(
    "Yahoo Finance",
    json_response=True,
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    allowed_origins=["*"],
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
# Run server
# ──────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="sse")