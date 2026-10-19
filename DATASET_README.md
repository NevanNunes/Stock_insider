# Synthetic Market Surveillance & Anomaly Detection Dataset

> This is a synthetic dataset created for an academic market-surveillance demonstration. The injected anomaly labels represent intentionally generated behavioral patterns and do not represent confirmed insider trading, actual market abuse, or real-world misconduct.

## 1. Purpose
Test bed for a cloud-based market-surveillance prototype that flags **statistically and behaviourally unusual trading for human review**. It supports trader profiling, Z-score detection, Isolation Forest, contextual (event/volume) detection, LOW/MEDIUM/HIGH risk classification, backend pipeline testing, a viva demo and evaluation against known synthetic anomalies. The system never claims to prove insider trading; alerts read *"Unusual trading activity detected. Further human review recommended."*

## 2. Synthetic nature
Everything is generated locally by `generate_dataset.py` with `numpy.random.default_rng(RANDOM_SEED)`. No real people, companies, prices, APIs or downloads. Same seed -> same dataset. Every row has `synthetic = True`.

## 3. Size (calculated from the generated files)
| Item | Count |
|---|---|
| Traders | 50 |
| Symbols (fictional) | 20 |
| Trading days | 92 (90 historical + 2 test) |
| Historical trades | 20,000 |
| Test trades | 500 (400 normal + 100 injected anomalies) |
| Market events | 150 |
| Feature rows | 20,500 |
| Naturally unusual historical trades (`is_natural_unusual`, NOT injected) | 389 |

## 4. Trader profiles
Six archetypes (Conservative, Active, Swing Trader, Momentum Trader, Sector-Focused, Diversified) are assigned at random to `TRD001..TRD050`. Each trader gets its own average quantity/notional and their std, trades per day, 2-6 preferred symbols (sector-focused traders: 2-3 sectors; diversified: distinct sectors), a preferred trading window and a BUY probability (about 30% of traders are strongly BUY- or SELL-skewed). So a Rs 10 lakh trade can be normal for one trader and extreme for another. `traders.csv` also stores the *realised* historical mean/std (`hist_*`).

## 5. Symbols
20 fictional companies across 12 sectors with different baseline price (Rs 100-4000), daily volatility (0.7%-3%), average daily volume and spread.

## 6. Historical trades
20,000 trades over 90 business days. Trades are allocated to traders in proportion to their rates (largest-remainder). Day, symbol (about 96% preferred), time (about 90% inside the preferred window; the rest fall just outside with an exponential offset), side and quantity are drawn from the trader's own profile. Prices come from per-symbol minute-level price paths (`new = prev x (1 + N(0, vol))`, overnight gaps and event shocks); the executed price adds half the symbol spread. `notional_value = quantity x price` always. About 2% of rows are *naturally unusual* (larger quantity or off-window time) and flagged with `is_natural_unusual = True`; `is_injected_anomaly` stays False for them.

## 7. Test trades
500 trades on the 2 trading days after the history: 400 normal trades generated like the historical ones plus 100 injected anomalies. Test days are short so the normal test density stays comparable with history.

## 8. Market events
150 fictional events (`EARNINGS`, `MERGER`, ... ) with LOW/MEDIUM/HIGH severity. Every symbol has several; 8 events fall in the test window (an event-enriched window so contextual anomalies can be evaluated). Events create price shocks and volume spikes.

## 9. Market volume
Daily `market_volume` per symbol/day (log-normal noise, rare random spikes, event-day spikes). `average_market_volume` = mean of the **previous** up-to-20 trading days (day 0 uses the configured ADV). `volume_ratio = market_volume / average_market_volume`, `volume_deviation = volume_ratio - 1`. All four columns are in `feature_dataset.csv`.

## 10. Feature engineering
Frequency (1h / 1d, plus per-symbol 1d), rolling buy/sell ratio (last 10 trades, `(buys+1)/(sells+1)`), `time_deviation` (minutes outside the preferred window, 0 inside), volume features, event features, price returns, smoothed `trader_symbol_frequency = (count+0.5)/(total+0.5x20)`, Z-scores.

## 11. Z-scores
`z = (x - mean) / std` using trader-specific history. Test trades use the frozen historical baseline; historical rows use an expanding **prior-only** baseline (z = 0 until 20 prior trades). If `std < 1e-6`, z = 0.

## 12. Isolation Forest inputs
`quantity, notional_value, trade_frequency_1h, trade_frequency_1d, buy_sell_ratio, time_deviation, volume_ratio, volume_deviation, price_return_before_trade, event_distance, trader_symbol_frequency`

Excluded: `price_return_after_trade`, `is_injected_anomaly`, `anomaly_type`, `expected_severity`. The Isolation Forest is fitted on historical rows only (`contamination=0.05`, `random_state=42` - project parameters, not universal truths).

## 13. Contextual features
`event_distance` (minutes to nearest event of that symbol), `is_pre_event` (within 24h before), `is_post_event` (within 24h after), volume features, `price_return_before_trade` (previous 60 trading minutes).

## 14. Anomaly injection (exactly 100)
| Type | Count | How |
|---|---|---|
| LARGE_TRADE | 20 | see below |
| LARGE_QUANTITY | 15 | see below |
| FREQUENCY_SPIKE | 15 | see below |
| UNUSUAL_SYMBOL | 10 | see below |
| UNUSUAL_TIME | 10 | see below |
| PRE_EVENT_ACTIVITY | 10 | see below |
| BEHAVIOR_CHANGE | 10 | see below |
| MULTI_FEATURE_ANOMALY | 10 | see below |

LARGE_TRADE uses a high-priced symbol (notional z>=3); LARGE_QUANTITY uses a low-priced symbol (quantity z>=3); FREQUENCY_SPIKE = two bursts of 8 and 7 trades within 30 minutes by low-frequency traders; UNUSUAL_SYMBOL uses a symbol with smoothed trader frequency <=1%; UNUSUAL_TIME is 60-180 minutes outside the window; PRE_EVENT_ACTIVITY = groups of large BUYs 5-90 minutes before a test event; BEHAVIOR_CHANGE = two strongly side-skewed traders flip side and double their size; MULTI_FEATURE_ANOMALY = clusters combining large quantity + rare symbol + off-window time + burst + high-volume day + pre-event.

## 15. Severity (deterministic, not random)
Signals: A = max(|notional z|,|quantity z|)>=3; B = 1h or 1d frequency >= 3x the trader's historical mean; C = time_deviation>=60; D = trader_symbol_frequency<=1%; E = volume_ratio>=2; F = is_pre_event. `signal_count = A+...+F` -> 1 LOW, 2 MEDIUM, >=3 HIGH; any |z|>=4 -> at least HIGH. An injected trade with `signal_count = 0` is LOW (floor). Non-injected rows have `expected_severity = NONE`. The signal columns are diagnostic only.

## 16. Ground truth
`is_injected_anomaly`, `anomaly_type`, `expected_severity` are evaluation-only and must never be model inputs. `expected_anomalies.csv` lists the injected rows.

## 17. Evaluation
Compare predictions with ground truth on the test set: TP/FP/TN/FN, precision, recall, F1, overall and per anomaly type (per-type FP/TN use the shared normal trades). Thresholds `|Z|<2 LOW`, `2<=|Z|<3 MEDIUM`, `|Z|>=3 HIGH` and the weights 40% statistical / 40% ML / 20% contextual are **project-defined experimental parameters, not regulatory standards**. The bundled reference detector (`data/reference_evaluation.csv`) alerts at the 95th percentile of historical combined scores; nothing is tuned to hit 100%.

## 18. Data-leakage prevention
- Frequencies are causal: only trades at or before the current timestamp (per trader, history + test merged by time); a future test trade never affects an earlier one.
- `average_market_volume` uses prior days only; Z-score baselines exclude the current trade.
- `price_return_after_trade` is **retrospective**: kept for analysis, **excluded from every real-time model**.
- Labels are never features.

## 19. Duplicate definition
Duplicate = same `(trader_id, symbol, timestamp, side, quantity, price)`. `trade_id` and `trade_code` are checked for global uniqueness separately.

## 20. Limitations
- Synthetic behaviour is simpler than real markets (no order book, no real cross-asset dynamics).
- `market_volume` is a daily total, used as a day-level volume regime; a live system would know only volume so far.
- Events are treated as known calendar entries; real unscheduled news would be unknown to a real-time system, so `event_distance` / `is_pre_event` are idealised.
- Raw `quantity` / `notional_value` in the Isolation Forest are not trader-normalised; this is deliberate so Z-scores add value.
- The test window is short (2 days) and event-enriched.
- Detection results depend on the injected patterns and project thresholds.

## 21. Regenerate
```
pip install numpy pandas scikit-learn
python generate_dataset.py
```
Change the constants at the top of the script (seed, sizes, anomaly counts) and re-run.
