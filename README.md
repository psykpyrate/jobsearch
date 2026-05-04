# Desktop Utilities

This workspace now contains two separate desktop apps:

- `python app.py` for the ETH/USDT bullish pattern scanner
- `python job_app.py` for a local job listing scanner focused on ZIP-code searches like `91607`

## Job Listing Scanner

`job_app.py` opens a desktop GUI that searches multiple job boards for local openings near your ZIP code.

Default search setup:

- ZIP: `91607`
- titles: `help desk`, `support analyst`
- boards: Indeed, ZipRecruiter, LinkedIn
- lookback: last 168 hours
- radius: 10 miles maximum

Features:

- Resolves a ZIP code into a city/state search location
- Searches each title separately, then merges and de-duplicates matches
- Lets you filter jobs by editable pay minimum and maximum values
- Lets you choose a pay interval like hourly, weekly, monthly, or yearly
- Includes quick pay presets for common hourly and yearly ranges
- Can auto-scan on a repeating minute interval
- Shows Windows desktop notifications when new matching jobs appear during later scans
- Lets you review results inside the app
- Opens the original job posting in your browser
- Exports all matches to CSV

Launch it with:

```powershell
python job_app.py
```

Install dependencies first:

```powershell
pip install -r requirements.txt
```

## Job Scanner Web App

`web_app.py` serves the HTML frontend and a live `/api/search` endpoint backed by the same Python scanner logic used by the desktop app.

Run it with:

```powershell
python web_app.py
```

Then open:

- `http://127.0.0.1:8080`

Useful options:

```powershell
python web_app.py --host 0.0.0.0 --port 8080
```

- Use `--host 0.0.0.0` if you want other devices on your local network to reach the server.
- The bundled HTML app lives in `html-app/` and now performs real live scans through the local Python API instead of mock data.
- If you publish the HTML frontend separately, it will still need a reachable hosted copy of the Python API for live searches.
- The published HTML app can be pointed at a separate backend by opening it with `?api=https://your-backend-host`.

### Deploying the backend

The easiest path for the current Python stack is a normal Python web host such as Render.

Why Render:

- As of May 3, 2026, Render documents free Python web services on its Hobby workspace plan, though they spin down after 15 minutes of inactivity and have monthly free usage limits. Source: [Deploy for Free – Render Docs](https://render.com/docs/free)
- Render also documents standard Python web services and dynamic `PORT` binding for deployments. Source: [Web Services – Render Docs](https://render.com/docs/web-services/), [Setting Your Python Version – Render Docs](https://render.com/docs/python-version)

This repo includes `render.yaml`, so you can deploy it directly from GitHub.

High-level deploy flow:

1. Push `C:\LT_Pybuilds\job scanner` to a GitHub repo.
2. In Render, create a new `Blueprint` or `Web Service` from that repo.
3. Let Render use:
   - build command: `pip install -r requirements.txt`
   - start command: `python web_app.py`
4. After deploy, copy your Render URL.
5. Open your Cloudflare Pages site with:

```text
https://ricosjobsearch.drumer.workers.dev/?api=https://your-render-service.onrender.com
```

Notes:

- The current backend is synchronous and intended for personal use/testing, not high traffic.
- Cold starts are expected on a free Render service after idle periods.
- Cloudflare Workers has first-class Python support as of April 23, 2026, but the current scanner depends on packages and scraping behavior that are a better fit for a regular Python host than a Worker runtime right now. Source: [Python Workers](https://developers.cloudflare.com/workers/languages/python/)

## ETH/USDT Bullish Pattern Scanner GUI

`app.py` gives you a desktop GUI for scanning and automatically backtesting bullish ETH/USDT candlestick setups.

Current focus:

- Morning Star
- Bullish Engulfing
- Hammer

Supported timeframes:

- 5m
- 15m
- 1h
- 2h
- 4h

Built-in confirmations:

- Trend context
- Volume increase
- Support proximity
- Previous resistance/level analysis with minimum bullish expansion filtering

## Quick start

1. Create a virtual environment.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Launch the GUI:

```powershell
python app.py
```

## Optional `.env` config

Place a `.env` file in the same folder as `app.py` if you want to override the market-data provider.

Supported keys:

- `MARKET_DATA_PROVIDER=binance_us`
- `MARKET_DATA_PROVIDER=binance`
- `MARKET_DATA_URL=https://your-provider.example/api/v3/klines`
- `MARKET_DATA_NAME=My Provider`

Example:

```env
MARKET_DATA_PROVIDER=binance_us
```

## What the GUI does

- Live scan across selected timeframes
- Automatic scan on app launch
- Automatic backtest refresh whenever a scan runs
- Auto-refresh on a timer
- Includes a `Run Self-Test` action and activity log so you can confirm the scanner is alive
- Filters signals to setups with more than `0.30%` projected bullish room from previous levels
- Shows `Watchlist` bullish candidates when strict confirmation rules do not pass
- Backtest bullish signals on Binance candles
- Tracks live predictions in a local log and grades them after enough candles pass
- Runs a simple parameter optimizer to compare confidence, target, and holding-bar settings
- Supports EMA trend filtering and RSI overbought filtering
- Simulates stop-loss and take-profit exits in backtests
- Ranks pattern/timeframe combinations in a scorecard using hit rate, return, confidence, and sample size
- Backtest from a local CSV file
- Export backtest trades to CSV

## CSV format

If you backtest from a local file, use columns:

- `open_time`
- `open`
- `high`
- `low`
- `close`
- `volume`
- optional `close_time`

## Notes

- Data source: Binance.US public klines first, then Binance global as a fallback.
- A `.env` file can override the provider order or replace the endpoint entirely.
- Confidence is a heuristic score, not a guarantee.
- The current build only surfaces bullish moves, as requested.
- Backtest wins are based on whether price exceeds the configured bullish move target, not just whether the final candle closes green.
- Live predictions are stored in `prediction_log.csv` beside the app and reviewed automatically on later scans/backtests.
- Zero or negative stop-loss / take-profit values mean those exit rules are turned off.
- Use `Run Self-Test` if you want to verify the app is processing data even when live market requests are unavailable.
- `Run Self-Test` uses a bundled synthetic file that is designed to trigger at least one bullish pattern.
- The live scan path is lighter than the optimizer path, so the window should remain more responsive during normal scanning.
- Pattern thresholds and backtest rules live in `crypto_scanner.py`.
