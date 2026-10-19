#!/usr/bin/env python3
"""
Synthetic Market Surveillance & Anomaly Detection Dataset Generator
===================================================================
Academic / demo use only.  Everything is generated locally with NumPy/pandas
(no external APIs, no real people, no real market data).

The injected anomaly labels are INTENTIONALLY GENERATED BEHAVIOURAL PATTERNS.
They do not represent confirmed insider trading or market abuse.

Run:   python generate_dataset.py
Needs: Python 3.11+, numpy, pandas, scikit-learn (scikit-learn only for the
       optional reference detector at the end).
"""
import math
import os
import sys

import numpy as np
import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================
RANDOM_SEED = 42

NUM_TRADERS = 50
NUM_SYMBOLS = 20

NUM_HISTORICAL_TRADES = 20_000
NUM_TEST_TRADES = 500

NUM_MARKET_EVENTS = 150
NUM_ANOMALIES = 100

OUTPUT_DIR = "data"

# --- secondary settings -------------------------------------------------------
NUM_HISTORICAL_DAYS = 90        # trading days of history
NUM_TEST_DAYS = 2               # trading days of the test window (60-120 total)
NUM_TEST_EVENTS = 8             # of the 150 events, how many fall in the test window
START_DATE = "2025-01-01"
OFF_PREFERRED_SYMBOL_PROB = 0.04
OFF_WINDOW_TIME_PROB = 0.10
NATURAL_UNUSUAL_RATE = 0.02     # ~2% naturally unusual historical trades (flagged separately)

ANOMALY_DISTRIBUTION = {
    "LARGE_TRADE": 20,
    "LARGE_QUANTITY": 15,
    "FREQUENCY_SPIKE": 15,
    "UNUSUAL_SYMBOL": 10,
    "UNUSUAL_TIME": 10,
    "PRE_EVENT_ACTIVITY": 10,
    "BEHAVIOR_CHANGE": 10,
    "MULTI_FEATURE_ANOMALY": 10,
}

SYMBOL_SMOOTHING_ALPHA = 0.5    # Laplace-style smoothing for trader_symbol_frequency
MIN_STD = 1e-6                  # z-score safety threshold
Z_MIN_HISTORY = 20              # min prior trades before an expanding z-score is trusted
BUY_SELL_WINDOW = 10            # trades in the rolling buy/sell ratio window

# Reference detector (project parameters, not universal truths)
IF_CONTAMINATION = 0.05
IF_RANDOM_STATE = 42
W_STAT, W_ML, W_CTX = 0.40, 0.40, 0.20

# --- market constants -------------------------------------------------------
SESSION_SEC = 375 * 60               # 09:15 -> 15:30
MIN_PER_DAY = 376                    # minute grid 0..375
OPEN_OFFSET_SEC = 9 * 3600 + 15 * 60
TZ = "Asia/Kolkata"

EVENT_TYPES = ["EARNINGS", "MERGER", "ACQUISITION", "MANAGEMENT_ANNOUNCEMENT",
               "MAJOR_CONTRACT", "REGULATORY_ANNOUNCEMENT", "PRODUCT_LAUNCH",
               "DIVIDEND_ANNOUNCEMENT", "COMPANY_NEWS"]
SEVERITIES = ["LOW", "MEDIUM", "HIGH"]

# Fictional companies: (symbol, name, sector)
CATALOG = [
    ("ALPHATECH", "Alpha Technologies Ltd", "IT"),
    ("BETACORP", "Beta Corporation Ltd", "Finance"),
    ("GAMMAIND", "Gamma Industries Ltd", "Manufacturing"),
    ("DELTAENG", "Delta Engineering Ltd", "Infrastructure"),
    ("EPSILONBANK", "Epsilon Bank Ltd", "Banking"),
    ("ZETAPHARMA", "Zeta Pharmaceuticals Ltd", "Pharma"),
    ("ETAMOTORS", "Eta Motors Ltd", "Automobile"),
    ("THETAENERGY", "Theta Energy Ltd", "Energy"),
    ("IOTATELECOM", "Iota Telecom Ltd", "Telecom"),
    ("KAPPAFMCG", "Kappa Consumer Goods Ltd", "FMCG"),
    ("LAMBDAINFRA", "Lambda Infrastructure Ltd", "Infrastructure"),
    ("MUFINANCE", "Mu Finance Ltd", "Finance"),
    ("NUHEALTH", "Nu Healthcare Ltd", "Healthcare"),
    ("XITECH", "Xi Technology Ltd", "Technology"),
    ("OMICRONMFG", "Omicron Manufacturing Ltd", "Manufacturing"),
    ("PIBANK", "Pi Bank Ltd", "Banking"),
    ("RHOSOFT", "Rho Software Ltd", "IT"),
    ("SIGMAPOWER", "Sigma Power Ltd", "Energy"),
    ("TAUAUTO", "Tau Automobiles Ltd", "Automobile"),
    ("UPSILONMEDS", "Upsilon Medicines Ltd", "Pharma"),
]

TYPE_CFG = {
    "Conservative":    dict(rate=(1.0, 2.5), notional=(30_000, 90_000),    cvq=(0.12, 0.18), npref=(2, 3), width=(90, 150)),
    "Active":          dict(rate=(8.0, 13.0), notional=(150_000, 600_000), cvq=(0.20, 0.30), npref=(4, 6), width=(200, 280)),
    "Swing Trader":    dict(rate=(0.8, 1.6), notional=(600_000, 2_000_000), cvq=(0.18, 0.28), npref=(3, 4), width=(120, 200)),
    "Momentum Trader": dict(rate=(5.0, 9.0), notional=(150_000, 500_000),  cvq=(0.25, 0.35), npref=(3, 5), width=(150, 240)),
    "Sector-Focused":  dict(rate=(3.0, 6.0), notional=(100_000, 400_000),  cvq=(0.20, 0.30), npref=(3, 6), width=(120, 220)),
    "Diversified":     dict(rate=(3.0, 5.0), notional=(100_000, 350_000),  cvq=(0.20, 0.30), npref=(5, 6), width=(150, 250)),
}

# Leakage control ---------------------------------------------------------------
GROUND_TRUTH_COLUMNS = ["is_injected_anomaly", "anomaly_type", "expected_severity"]
RETROSPECTIVE_COLUMNS = ["price_return_after_trade"]
MODEL_FEATURES = [
    "quantity", "notional_value", "trade_frequency_1h", "trade_frequency_1d",
    "buy_sell_ratio", "time_deviation", "volume_ratio", "volume_deviation",
    "price_return_before_trade", "event_distance", "trader_symbol_frequency",
]
PROHIBITED_MODEL_INPUTS = GROUND_TRUTH_COLUMNS + RETROSPECTIVE_COLUMNS

rng = np.random.default_rng(RANDOM_SEED)
W = {}   # shared world state (prices, volumes, calendar ...)


# =============================================================================
# HELPERS
# =============================================================================
def validate_config():
    assert NUM_ANOMALIES <= NUM_TEST_TRADES, "NUM_ANOMALIES must be <= NUM_TEST_TRADES"
    normal_test = NUM_TEST_TRADES - NUM_ANOMALIES
    assert normal_test + NUM_ANOMALIES == NUM_TEST_TRADES
    assert sum(ANOMALY_DISTRIBUTION.values()) == NUM_ANOMALIES, \
        "ANOMALY_DISTRIBUTION must sum to NUM_ANOMALIES"
    assert NUM_SYMBOLS <= len(CATALOG), "NUM_SYMBOLS exceeds the fictional catalogue"
    assert 60 <= NUM_HISTORICAL_DAYS + NUM_TEST_DAYS <= 120, "use roughly 60-120 trading days"
    assert NUM_TEST_EVENTS <= NUM_SYMBOLS and NUM_TEST_EVENTS < NUM_MARKET_EVENTS
    assert not set(MODEL_FEATURES) & set(PROHIBITED_MODEL_INPUTS), "leakage in MODEL_FEATURES"


def alloc(total, weights):
    """Largest-remainder allocation of `total` items proportionally to weights."""
    w = np.asarray(weights, float)
    w = w / w.sum()
    raw = w * total
    base = np.floor(raw).astype(int)
    rem = int(total - base.sum())
    order = np.argsort(-(raw - base))
    base[order[:rem]] += 1
    return base


def split_counts(total, parts):
    parts = max(1, min(parts, total))
    base, rem = divmod(total, parts)
    return [base + 1 if i < rem else base for i in range(parts)]


def choose_pool(pool, n):
    pool = np.asarray(pool)
    return rng.choice(pool, n, replace=n > len(pool))


def hhmm(minutes_from_open):
    m = 9 * 60 + 15 + int(minutes_from_open)
    return f"{m // 60:02d}:{m % 60:02d}"


# =============================================================================
# SYMBOLS, CALENDAR, EVENTS
# =============================================================================
def build_symbols():
    cat = CATALOG[:NUM_SYMBOLS]
    n = len(cat)
    return pd.DataFrame({
        "symbol": [c[0] for c in cat],
        "company_name": [c[1] for c in cat],
        "sector": [c[2] for c in cat],
        "baseline_price": np.exp(rng.uniform(np.log(100), np.log(4000), n)).round(2),
        "volatility": rng.uniform(0.007, 0.03, n).round(4),      # daily return std
        "average_daily_volume": np.round(np.exp(rng.uniform(np.log(2e5), np.log(5e6), n)), -3).astype(int),
        "typical_spread": rng.uniform(0.0004, 0.0025, n).round(5),  # fraction of price
    })


def build_events(sym_df, dates):
    symbols = sym_df.symbol.tolist()
    n_test = NUM_TEST_EVENTS
    n_hist = NUM_MARKET_EVENTS - n_test
    reps = min(3, n_hist // len(symbols))            # every symbol gets >= reps events
    hs = list(np.tile(symbols, reps)) + rng.choice(symbols, n_hist - reps * len(symbols)).tolist()
    hs = rng.permutation(hs).tolist()
    h_day = rng.integers(0, NUM_HISTORICAL_DAYS, n_hist)
    h_min = rng.integers(15, 361, n_hist)
    h_sev = rng.choice(SEVERITIES, n_hist, p=[0.40, 0.35, 0.25])

    # Test window is deliberately event-enriched so contextual anomalies can be evaluated.
    ts_syms = rng.choice(symbols, n_test, replace=False).tolist()
    t_day = np.array([NUM_HISTORICAL_DAYS + (i % NUM_TEST_DAYS) for i in range(n_test)])
    t_min = rng.integers(105, 316, n_test)           # 11:00 - 14:30
    n_high = int(math.ceil(0.6 * n_test))
    t_sev = rng.permutation(["HIGH"] * n_high + ["MEDIUM"] * (n_test - n_high))

    ev = pd.DataFrame({
        "symbol": hs + ts_syms,
        "day_idx": np.concatenate([h_day, t_day]),
        "minute_idx": np.concatenate([h_min, t_min]),
        "event_severity": np.concatenate([h_sev, t_sev]),
    })
    ev["second"] = rng.integers(0, 60, len(ev))
    ev["event_type"] = rng.choice(EVENT_TYPES, len(ev))
    ev["abs_ts"] = (W["ord_days"][ev["day_idx"].values] * 86400 + OPEN_OFFSET_SEC
                  + ev["minute_idx"].values * 60 + ev["second"].values)
    ev = ev.sort_values("abs_ts").reset_index(drop=True)
    ev["event_id"] = [f"EVT{i + 1:04d}" for i in range(len(ev))]
    names = dict(zip(sym_df.symbol, sym_df.company_name))
    ev["description"] = [
        f"Fictional {t.lower().replace('_', ' ')} event for {names[s]} ({sev.lower()} severity)"
        for t, s, sev in zip(ev.event_type, ev.symbol, ev.event_severity)]
    ts = (W["dates_np"][ev["day_idx"].values]
          + (OPEN_OFFSET_SEC + ev["minute_idx"].values * 60 + ev["second"].values).astype("timedelta64[s]"))
    ev["event_timestamp"] = [t.isoformat(sep=" ") for t in pd.DatetimeIndex(ts).tz_localize(TZ)]
    return ev


def build_price_paths(sym_df, events):
    n = W["n_days"] * MIN_PER_DAY
    P = np.empty((len(sym_df), n))
    shock = {"LOW": 0.004, "MEDIUM": 0.012, "HIGH": 0.03}
    for si, row in sym_df.iterrows():
        v = row.volatility
        r = rng.normal(0, v / np.sqrt(375), n)                    # return_value = N(0, vol)
        r[::MIN_PER_DAY] = rng.normal(0, v * 0.5, W["n_days"])    # overnight gap
        r[0] = 0.0
        for e in events[events.symbol == row.symbol].itertuples():
            r[e.day_idx * MIN_PER_DAY + e.minute_idx] += (
                rng.choice([-1, 1]) * shock[e.event_severity] * rng.uniform(0.5, 1.5))
        r = np.clip(r, -0.25, 0.25)
        P[si] = row.baseline_price * np.cumprod(1 + r)            # new = prev * (1 + return)
    assert (P > 0).all()
    return P


def build_volumes(sym_df, events):
    nd, ns = W["n_days"], len(sym_df)
    mv = np.zeros((nd, ns))
    for s, row in sym_df.iterrows():
        f = np.exp(rng.normal(0, 0.15, nd))                       # ~0.7-1.4 on normal days
        spike = rng.random(nd) < 0.02
        f = np.where(spike, f * rng.uniform(2.0, 3.0, nd), f)
        mv[:, s] = row.average_daily_volume * f
    sidx = {s: i for i, s in enumerate(sym_df.symbol)}
    for e in events.itertuples():
        s, d = sidx[e.symbol], e.day_idx
        if e.event_severity == "HIGH":
            m, prev = rng.uniform(2.6, 3.6), rng.uniform(1.15, 1.5)
        elif e.event_severity == "MEDIUM":
            m, prev = rng.uniform(1.5, 2.2), rng.uniform(1.05, 1.3)
        else:
            m, prev = rng.uniform(1.0, 1.25), 1.0
        mv[d, s] *= m
        if d > 0:
            mv[d - 1, s] *= prev
        if d + 1 < nd:
            mv[d + 1, s] *= rng.uniform(1.0, 1.2)
    mv = np.round(mv).astype(np.int64)
    avg = np.empty((nd, ns))
    for d in range(nd):                                           # PRIOR days only
        avg[d] = sym_df.average_daily_volume.values if d == 0 else mv[max(0, d - 20):d].mean(axis=0)
    return mv, np.round(avg, 2)


# =============================================================================
# TRADERS
# =============================================================================
def build_traders(sym_df):
    n = len(sym_df)
    sectors = sym_df.sector.values
    prices = sym_df.baseline_price.values
    uniq_sec = sorted(set(sectors))
    types = list(TYPE_CFG)
    assign = rng.permutation(np.resize(types, NUM_TRADERS))
    traders = []
    for i in range(NUM_TRADERS):
        ttype = str(assign[i])
        cfg = TYPE_CFG[ttype]
        npref = int(rng.integers(cfg["npref"][0], cfg["npref"][1] + 1))
        if ttype == "Sector-Focused":
            chosen, pref = [], []
            for s in rng.permutation(uniq_sec):
                chosen.append(s)
                pref = [j for j in range(n) if sectors[j] in chosen]
                if len(pref) >= 3:
                    break
            if len(pref) > 6:
                pref = rng.choice(pref, 6, replace=False).tolist()
        elif ttype == "Diversified":
            pref, seen = [], set()
            for j in rng.permutation(n):
                if sectors[j] not in seen:
                    pref.append(int(j)); seen.add(sectors[j])
                if len(pref) == npref:
                    break
        else:
            pref = rng.choice(n, npref, replace=False).tolist()
        pref = np.array(sorted(int(p) for p in pref))
        pw = rng.dirichlet(np.full(len(pref), 2.0))

        avg_notional = float(np.exp(rng.uniform(np.log(cfg["notional"][0]), np.log(cfg["notional"][1]))))
        geo = float(np.exp(np.mean(np.log(prices[pref]))))
        avg_q = max(5.0, round(avg_notional / geo))
        cvq = rng.uniform(*cfg["cvq"])
        q_std = max(1.0, cvq * avg_q)
        pcv = float(np.std(prices[pref]) / np.mean(prices[pref]))
        width = int(rng.uniform(*cfg["width"]) // 5 * 5)
        ws = int(rng.uniform(0, 375 - width) // 5 * 5)
        if rng.random() < 0.30:
            bp = float(rng.choice([0.72, 0.28]) + rng.uniform(-0.04, 0.04))
        else:
            bp = float(rng.uniform(0.45, 0.58))
        traders.append(dict(
            idx=i, trader_id=f"TRD{i + 1:03d}", type=ttype,
            rate=float(rng.uniform(*cfg["rate"])),
            avg_q=float(avg_q), q_std=float(q_std),
            avg_notional=avg_notional, notional_std=avg_notional * math.sqrt(cvq ** 2 + pcv ** 2),
            pref_idx=pref, pref_w=pw, pref_sectors=sorted(set(sectors[pref])),
            ws=ws, we=ws + width, buy_prob=bp))
    return traders


# =============================================================================
# TRADE GENERATION
# =============================================================================
def _price_vec(df):
    minute = np.minimum(df["sec"].values // 60, 375)
    idx = df["day"].values * MIN_PER_DAY + minute
    si = df["sym_idx"].values
    base = W["P"][si, idx]
    half = W["spread"][si] / 2
    sgn = np.where(df["side"].values == "BUY", 1, -1)
    return np.round(base * (1 + sgn * half), 2)


def price_at(si, day, sec, side):
    idx = day * MIN_PER_DAY + min(int(sec) // 60, 375)
    half = W["spread"][si] / 2
    return round(float(W["P"][si, idx]) * (1 + (half if side == "BUY" else -half)), 2)


def gen_normal_trades(traders, counts, day_range, dataset, natural):
    days = np.arange(*day_range)
    thr = np.percentile(W["day_move"][:NUM_HISTORICAL_DAYS], 75)
    frames = []
    for t, n in zip(traders, counts):
        if n == 0:
            continue
        w = np.ones(len(days))
        if t["type"] == "Momentum Trader":                 # more activity on big-move days
            w = w + 1.5 * (W["day_move"][days] > thr)
        day = rng.choice(days, size=n, p=w / w.sum())
        other = np.setdiff1d(np.arange(W["ns"]), t["pref_idx"])
        sym = rng.choice(t["pref_idx"], size=n, p=t["pref_w"])
        if len(other):
            sym = np.where(rng.random(n) < OFF_PREFERRED_SYMBOL_PROB, rng.choice(other, n), sym)
        # time of day: mostly inside the preferred window, sometimes just outside it
        inside = rng.random(n) >= OFF_WINDOW_TIME_PROB
        sec_in = rng.uniform(t["ws"] * 60, t["we"] * 60, n)
        left = rng.random(n) < 0.5
        left = np.where(t["ws"] < 20, False, np.where(t["we"] > 355, True, left))
        room = np.where(left, t["ws"] * 60, SESSION_SEC - t["we"] * 60).astype(float)
        off = np.minimum(rng.exponential(25 * 60, n), room * rng.uniform(0.6, 1.0, n))
        sec_out = np.where(left, t["ws"] * 60 - off, t["we"] * 60 + off)
        sec = np.where(inside, sec_in, sec_out)
        side = np.where(rng.random(n) < t["buy_prob"], "BUY", "SELL")
        qty = np.maximum(1, np.round(rng.normal(t["avg_q"], t["q_std"], n))).astype(float)
        nat = (rng.random(n) < NATURAL_UNUSUAL_RATE) if natural else np.zeros(n, bool)
        for k in np.where(nat)[0]:                          # naturally unusual (not injected)
            opts = []
            if t["ws"] >= 70: opts.append("L")
            if SESSION_SEC / 60 - t["we"] >= 70: opts.append("R")
            if rng.random() < 0.6 or not opts:
                qty[k] = math.ceil(qty[k] * rng.uniform(1.4, 2.0))
            else:
                dev = rng.uniform(60, min(150, t["ws"] if rng.choice(opts) == "L" else 150)) * 60
                sec[k] = (t["ws"] * 60 - dev) if (rng.choice(opts) == "L") else (t["we"] * 60 + dev)
        frames.append(pd.DataFrame({
            "trader_id": t["trader_id"], "sym_idx": sym, "side": side,
            "quantity": qty.astype(int), "day": day,
            "sec": np.clip(np.round(sec), 0, SESSION_SEC).astype(int),
            "is_natural_unusual": nat, "is_injected_anomaly": False,
            "anomaly_type": "NONE", "dataset": dataset}))
    return pd.concat(frames, ignore_index=True)


def finalize(raw):
    """Add price / notional / timestamp / session columns; make duplicates impossible."""
    df = raw.copy().reset_index(drop=True)
    df["day"] = df["day"].astype(int)
    df["sec"] = df["sec"].astype(int)
    key = ["trader_id", "sym_idx", "day", "sec", "side", "quantity", "price"]
    for _ in range(200):
        df["price"] = _price_vec(df)
        dup = df.duplicated(subset=key, keep="first")
        if not dup.any():
            break
        df.loc[dup, "sec"] = np.where(df.loc[dup, "sec"] > 0, df.loc[dup, "sec"] - 1, df.loc[dup, "sec"] + 1)
    df["symbol"] = W["symbols"][df["sym_idx"].values]
    df["sector"] = W["sectors"][df["sym_idx"].values]
    df["notional_value"] = np.round(df["quantity"].values * df["price"].values, 2)
    ts = pd.DatetimeIndex(W["dates_np"][df["day"].values]
                          + (OPEN_OFFSET_SEC + df["sec"].values).astype("timedelta64[s]")).tz_localize(TZ)
    df["timestamp"] = [t.isoformat(sep=" ") for t in ts]
    df["trade_date"] = ts.strftime("%Y-%m-%d")
    df["trade_time"] = ts.strftime("%H:%M:%S")
    df["market_session"] = np.where(df["sec"] < 2700, "OPEN", np.where(df["sec"] < 20700, "MID_SESSION", "CLOSE"))
    df["synthetic"] = True
    df["ts_abs"] = W["ord_days"][df["day"].values] * 86400 + OPEN_OFFSET_SEC + df["sec"].values
    return df


# =============================================================================
# ANOMALY INJECTION
# =============================================================================
def inject_anomalies(traders, stats, events):
    td = list(range(NUM_HISTORICAL_DAYS, W["n_days"]))
    rows = []
    K = W["ns"]
    a = SYMBOL_SMOOTHING_ALPHA

    def add(t, si, side, qty, day, sec, atype):
        rows.append(dict(trader_id=t["trader_id"], sym_idx=int(si), side=side,
                         quantity=int(max(1, qty)), day=int(day), sec=int(round(sec)),
                         is_natural_unusual=False, is_injected_anomaly=True,
                         anomaly_type=atype, dataset="TEST"))

    def in_window_sec(t):
        return rng.uniform(t["ws"] * 60 + 60, t["we"] * 60 - 60)

    def side_of(t):
        return "BUY" if rng.random() < t["buy_prob"] else "SELL"

    def normal_qty(t):
        return max(1, round(rng.normal(t["avg_q"], t["q_std"])))

    def sym_smoothed(t, si):
        s = stats[t["trader_id"]]
        return (s["counts"][si] + a) / (s["n"] + a * K)

    all_idx = np.arange(NUM_TRADERS)
    low_rate = [t["idx"] for t in traders if t["type"] in ("Conservative", "Swing Trader")]

    # ---------------------------------------------------------------- MULTI first (reserves events)
    n = ANOMALY_DISTRIBUTION["MULTI_FEATURE_ANOMALY"]
    sizes = split_counts(n, 2)
    test_ev = events[events["day_idx"] >= NUM_HISTORICAL_DAYS]
    sidx = {s: i for i, s in enumerate(W["symbols"])}
    cand_ev = []
    for e in test_ev.itertuples():
        ratio = W["mv"][e.day_idx, sidx[e.symbol]] / W["avg_mv"][e.day_idx, sidx[e.symbol]]
        if ratio >= 2.0:
            cand_ev.append(e)
    used_ev, used_tr = set(), set()
    for m in sizes:
        found = False
        for relax in (0, 1):
            for e in rng.permutation(len(cand_ev)):
                ev = cand_ev[int(e)]
                if ev.event_id in used_ev:
                    continue
                for ti in rng.permutation(NUM_TRADERS):
                    t = traders[int(ti)]
                    if t["idx"] in used_tr:
                        continue
                    if relax == 0 and t["idx"] not in low_rate:
                        continue
                    si = sidx[ev.symbol]
                    if sym_smoothed(t, si) > 0.01:
                        continue
                    T = ev.minute_idx * 60 + ev.second
                    span = 20 * 60
                    ivs = []
                    hi_e = min(t["ws"] * 60 - 3600, T - 300)
                    if hi_e >= span:
                        ivs.append((0, hi_e))
                    lo_l, hi_l = t["we"] * 60 + 3600, T - 300
                    if hi_l - lo_l >= span:
                        ivs.append((lo_l, hi_l))
                    if not ivs:
                        continue
                    lo, hi = ivs[int(rng.integers(len(ivs)))]
                    start = rng.uniform(lo, hi - span)
                    times = np.sort(rng.uniform(start, start + span, m))
                    s = stats[t["trader_id"]]
                    for tm in times:
                        add(t, si, "BUY", math.ceil(s["mean_q"] + rng.uniform(3.2, 5.0) * s["std_q"]),
                            ev.day_idx, tm, "MULTI_FEATURE_ANOMALY")
                    used_ev.add(ev.event_id); used_tr.add(t["idx"]); found = True
                    break
                if found: break
            if found: break
        if not found:
            raise RuntimeError("Could not place a MULTI_FEATURE_ANOMALY cluster; try another seed")

    # ---------------------------------------------------------------- LARGE_TRADE
    for ti in choose_pool(all_idx, ANOMALY_DISTRIBUTION["LARGE_TRADE"]):
        t = traders[int(ti)]; s = stats[t["trader_id"]]
        si = int(t["pref_idx"][np.argmax(W["base_price"][t["pref_idx"]])])   # high-priced name
        day, sec, side = int(rng.choice(td)), in_window_sec(t), side_of(t)
        p = price_at(si, day, sec, side)
        target = s["mean_n"] + rng.uniform(3.2, 7.0) * s["std_n"]
        add(t, si, side, math.ceil(target / p), day, sec, "LARGE_TRADE")

    # ---------------------------------------------------------------- LARGE_QUANTITY
    for ti in choose_pool(all_idx, ANOMALY_DISTRIBUTION["LARGE_QUANTITY"]):
        t = traders[int(ti)]; s = stats[t["trader_id"]]
        si = int(t["pref_idx"][np.argmin(W["base_price"][t["pref_idx"]])])   # low-priced name
        add(t, si, side_of(t), math.ceil(s["mean_q"] + rng.uniform(3.1, 6.0) * s["std_q"]),
            int(rng.choice(td)), in_window_sec(t), "LARGE_QUANTITY")

    # ---------------------------------------------------------------- FREQUENCY_SPIKE
    sizes = split_counts(ANOMALY_DISTRIBUTION["FREQUENCY_SPIKE"], 2)
    for m, ti in zip(sizes, rng.choice(low_rate, len(sizes), replace=False)):
        t = traders[int(ti)]
        day = int(rng.choice(td))
        t0 = rng.uniform(t["ws"] * 60, t["we"] * 60 - 30 * 60)
        for tm in np.sort(rng.uniform(t0, t0 + 30 * 60, m)):
            add(t, rng.choice(t["pref_idx"], p=t["pref_w"]), side_of(t), normal_qty(t), day, tm, "FREQUENCY_SPIKE")

    # ---------------------------------------------------------------- UNUSUAL_SYMBOL
    n, got = ANOMALY_DISTRIBUTION["UNUSUAL_SYMBOL"], 0
    for ti in rng.permutation(NUM_TRADERS):
        if got >= n: break
        t = traders[int(ti)]; s = stats[t["trader_id"]]
        if s["n"] < 80: continue
        cnt = s["counts"].astype(float).copy()
        cnt[t["pref_idx"]] = 1e9
        cands = [j for j in range(K) if cnt[j] == cnt.min() and sym_smoothed(t, j) <= 0.01]
        if not cands: continue
        add(t, int(rng.choice(cands)), side_of(t), normal_qty(t), int(rng.choice(td)),
            in_window_sec(t), "UNUSUAL_SYMBOL")
        got += 1
    assert got == n, "not enough traders for UNUSUAL_SYMBOL"

    # ---------------------------------------------------------------- UNUSUAL_TIME
    n, got = ANOMALY_DISTRIBUTION["UNUSUAL_TIME"], 0
    for ti in rng.permutation(NUM_TRADERS):
        if got >= n: break
        t = traders[int(ti)]
        opts = []
        if t["ws"] >= 65: opts.append(("L", t["ws"]))
        if 375 - t["we"] >= 65: opts.append(("R", 375 - t["we"]))
        if not opts: continue
        side_, room = opts[int(rng.integers(len(opts)))]
        dev = rng.uniform(60, min(room - 2, 180)) * 60
        sec = t["ws"] * 60 - dev if side_ == "L" else t["we"] * 60 + dev
        add(t, rng.choice(t["pref_idx"], p=t["pref_w"]), side_of(t), normal_qty(t),
            int(rng.choice(td)), sec, "UNUSUAL_TIME")
        got += 1
    assert got == n, "not enough traders with room for UNUSUAL_TIME"

    # ---------------------------------------------------------------- PRE_EVENT_ACTIVITY
    n = ANOMALY_DISTRIBUTION["PRE_EVENT_ACTIVITY"]
    left = [e for e in test_ev.itertuples() if e.event_id not in used_ev]
    groups = split_counts(n, min(4, len(left)))
    for m, ei in zip(groups, rng.choice(len(left), len(groups), replace=False)):
        ev = left[int(ei)]
        si = sidx[ev.symbol]
        fav = [t for t in traders if si in t["pref_idx"]]
        t = (fav if fav else traders)[int(rng.integers(len(fav if fav else traders)))]
        s = stats[t["trader_id"]]
        T = ev.minute_idx * 60 + ev.second
        offs = np.sort(rng.uniform(5 * 60, 90 * 60, m))[::-1]
        for o in offs:
            add(t, si, "BUY", math.ceil(s["mean_q"] + rng.uniform(2.2, 4.0) * s["std_q"]),
                ev.day_idx, T - o, "PRE_EVENT_ACTIVITY")

    # ---------------------------------------------------------------- BEHAVIOR_CHANGE
    n = ANOMALY_DISTRIBUTION["BEHAVIOR_CHANGE"]
    skew = sorted([t for t in traders if stats[t["trader_id"]]["n"] >= 100],
                  key=lambda t: -abs(t["buy_prob"] - 0.5))
    sizes = split_counts(n, 2)
    for m, t in zip(sizes, skew[:2]):
        new_side = "SELL" if t["buy_prob"] >= 0.5 else "BUY"
        secs = np.sort(rng.uniform(t["ws"] * 60 + 60, t["we"] * 60 - 60, m))
        for k, sc in enumerate(secs):
            add(t, rng.choice(t["pref_idx"], p=t["pref_w"]), new_side,
                round(t["avg_q"] * rng.uniform(1.8, 2.6)), td[k % len(td)], sc, "BEHAVIOR_CHANGE")

    return pd.DataFrame(rows)


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================
def causal_window_counts(ts, window):
    """Trades with ts in (t-window, t] that occur at or before the current row (no future rows)."""
    left = np.searchsorted(ts, ts - window, side="right")
    return np.arange(len(ts)) - left + 1


def grouped_window_counts(df, keys, window):
    out = np.zeros(len(df), dtype=int)
    tsv = df["ts_abs"].values
    for _, idx in df.groupby(keys, sort=False).indices.items():
        out[idx] = causal_window_counts(tsv[idx], window)
    return out


def build_features(all_df, traders, events):
    df = all_df.sort_values(["ts_abs", "trade_id"]).reset_index(drop=True)
    is_hist = (df["dataset"] == "HISTORICAL").values

    # --- frequency (causal / streaming) ------------------------------------
    df["trade_frequency_1h"] = grouped_window_counts(df, "trader_id", 3600)
    df["trade_frequency_1d"] = grouped_window_counts(df, "trader_id", 86400)
    df["trade_frequency_symbol_1d"] = grouped_window_counts(df, ["trader_id", "symbol"], 86400)

    # --- rolling buy/sell ratio (causal, last BUY_SELL_WINDOW trades incl. current) ---
    df["_is_buy"] = (df["side"] == "BUY").astype(int)
    buys = df.groupby("trader_id")["_is_buy"].transform(
        lambda s: s.rolling(BUY_SELL_WINDOW, min_periods=1).sum()
    )
    nwin = df.groupby("trader_id").cumcount().add(1).clip(upper=BUY_SELL_WINDOW)
    sells = nwin - buys
    df["buy_sell_ratio"] = ((buys + 1) / (sells + 1)).round(4)

    # --- time deviation (deterministic from timestamp + preferred window) -----
    ws = df["trader_id"].map({t["trader_id"]: t["ws"] for t in traders}).values
    we = df["trader_id"].map({t["trader_id"]: t["we"] for t in traders}).values
    m = df["sec"].values / 60.0
    df["time_deviation"] = np.round(np.maximum.reduce([ws - m, m - we, np.zeros(len(df))]), 4)

    # --- market volume ---------------------------------------------------------
    d, s = df["day"].values, df["sym_idx"].values
    df["market_volume"] = W["mv"][d, s]
    df["average_market_volume"] = W["avg_mv"][d, s]
    df["volume_ratio"] = (df["market_volume"] / df["average_market_volume"]).round(6)
    df["volume_deviation"] = (df["volume_ratio"] - 1).round(6)

    # --- events ---------------------------------------------------------------------
    ev_abs = {sym: events.loc[events.symbol == sym, "abs_ts"].values for sym in W["symbols"]}
    dist = np.zeros(len(df)); pre = np.zeros(len(df), int); post = np.zeros(len(df), int)
    for sym, idx in df.groupby("symbol").indices.items():
        diff = ev_abs[sym][None, :] - df["ts_abs"].values[idx][:, None]
        dist[idx] = np.abs(diff).min(axis=1) / 60.0
        pre[idx] = ((diff >= 0) & (diff <= 86400)).any(axis=1)
        post[idx] = ((diff < 0) & (diff >= -86400)).any(axis=1)
    df["event_distance"] = dist.round(2)
    df["is_pre_event"] = pre
    df["is_post_event"] = post

    # --- price returns ---------------------------------------------------------------
    idx = d * MIN_PER_DAY + np.minimum(df["sec"].values // 60, 375)
    Pm = W["P"]; last = Pm.shape[1] - 1
    df["price_return_before_trade"] = (Pm[s, idx] / Pm[s, np.maximum(idx - 60, 0)] - 1).round(6)
    # RETROSPECTIVE / OUTCOME feature: must never be used by the real-time detector
    df["price_return_after_trade"] = (Pm[s, np.minimum(idx + 60, last)] / Pm[s, idx] - 1).round(6)

    # --- trader_symbol_frequency (smoothed) ----------------------------------------
    a, K = SYMBOL_SMOOTHING_ALPHA, W["ns"]
    h = df[is_hist]
    prev_sym = h.groupby(["trader_id", "symbol"]).cumcount().values
    prev_tr = h.groupby("trader_id").cumcount().values
    tsf = np.zeros(len(df))
    tsf[is_hist] = (prev_sym + a) / (prev_tr + a * K)          # prior trades only
    tot = h.groupby("trader_id").size()
    cnt = h.groupby(["trader_id", "symbol"]).size()
    te = df[~is_hist]
    c = np.array([cnt.get((tr, sy), 0) for tr, sy in zip(te.trader_id, te.symbol)])
    n_tot = te.trader_id.map(tot).values
    tsf[~is_hist] = (c + a) / (n_tot + a * K)                  # frozen historical baseline
    df["trader_symbol_frequency"] = np.round(tsf, 6)

    # --- z-scores -----------------------------------------------------------------------
    def z_cols(col):
        z = np.zeros(len(df))
        g = h.groupby("trader_id")[col]
        n_prev = g.cumcount().values.astype(float)
        x = h[col].values.astype(float)
        s1 = g.cumsum().values - x
        s2 = (h[col].astype(float) ** 2).groupby(h["trader_id"]).cumsum().values - x ** 2
        with np.errstate(divide="ignore", invalid="ignore"):
            mean = s1 / n_prev
            var = (s2 - n_prev * mean ** 2) / (n_prev - 1)
        sd = np.sqrt(np.maximum(var, 0))
        ok = (n_prev >= Z_MIN_HISTORY) & (sd >= MIN_STD)
        zh = np.where(ok, (x - mean) / np.where(sd < MIN_STD, 1, sd), 0.0)   # expanding, prior-only
        z[is_hist] = zh
        mu = h.groupby("trader_id")[col].mean()
        sg = h.groupby("trader_id")[col].std()                                # frozen hist baseline
        mu_t, sg_t = te.trader_id.map(mu).values, te.trader_id.map(sg).values
        zt = np.where(sg_t >= MIN_STD, (te[col].values - mu_t) / np.where(sg_t < MIN_STD, 1, sg_t), 0.0)
        z[~is_hist] = zt
        return np.round(z, 4)

    df["notional_zscore"] = z_cols("notional_value")
    df["quantity_zscore"] = z_cols("quantity")

    # --- deterministic severity signals (evaluation-only) --------------------------
    base1h = h.groupby("trader_id")["trade_frequency_1h"].mean()
    base1d = h.groupby("trader_id")["trade_frequency_1d"].mean()
    b1h, b1d = df.trader_id.map(base1h).values, df.trader_id.map(base1d).values
    df["signal_A"] = (np.maximum(df.notional_zscore.abs(), df.quantity_zscore.abs()) >= 3).astype(int)
    df["signal_B"] = ((df.trade_frequency_1h >= 3 * b1h) | (df.trade_frequency_1d >= 3 * b1d)).astype(int)
    df["signal_C"] = (df.time_deviation >= 60).astype(int)
    df["signal_D"] = (df.trader_symbol_frequency <= 0.01).astype(int)
    df["signal_E"] = (df.volume_ratio >= 2).astype(int)
    df["signal_F"] = (df.is_pre_event == 1).astype(int)
    df["signal_count"] = df[[f"signal_{c}" for c in "ABCDEF"]].sum(axis=1)
    sev = np.where(df.signal_count >= 3, "HIGH", np.where(df.signal_count == 2, "MEDIUM", "LOW"))
    strong = (df.notional_zscore.abs() >= 4) | (df.quantity_zscore.abs() >= 4)
    sev = np.where(strong, "HIGH", sev)
    df["expected_severity"] = np.where(df.is_injected_anomaly, sev, "NONE")
    return df.drop(columns=["_is_buy"]), base1h, base1d


# =============================================================================
# REFERENCE DETECTOR (optional; demonstrates leakage-free use of the features)
# =============================================================================
def explain(r, b1h, b1d, hist_ratio):
    why = []
    if abs(r.notional_zscore) >= 3:
        why.append(f"Notional value was {abs(r.notional_zscore):.1f} standard deviations "
                   f"{'above' if r.notional_zscore > 0 else 'below'} the trader's historical average.")
    if abs(r.quantity_zscore) >= 3:
        why.append(f"Quantity was {abs(r.quantity_zscore):.1f} standard deviations "
                   f"{'above' if r.quantity_zscore > 0 else 'below'} the trader's historical average.")
    if r.trade_frequency_1h >= 3 * b1h or r.trade_frequency_1d >= 3 * b1d:
        why.append(f"Trading frequency was significantly higher than normal "
                   f"({r.trade_frequency_1h} trades in the last hour).")
    if r.trader_symbol_frequency <= 0.01:
        why.append("The symbol is rarely traded by this trader.")
    if r.time_deviation >= 60:
        why.append(f"The trade occurred {r.time_deviation:.0f} minutes outside the trader's preferred window.")
    if r.volume_ratio >= 2:
        why.append("Market volume was significantly above its historical average.")
    if r.is_pre_event == 1:
        why.append("The trade occurred shortly before a synthetic market event.")
    if hist_ratio > 0 and abs(math.log(r.buy_sell_ratio / hist_ratio)) >= math.log(3):
        why.append("The recent buy/sell mix deviates from the trader's historical pattern.")
    if not why:
        why.append("The combination of features is unusual in the multivariate (Isolation Forest) view.")
    return ("Unusual trading activity detected. Further human review recommended.\n"
            "Trade flagged because:\n" + "\n".join(f"- {w}" for w in why))


def run_reference_detector(feat, base1h, base1d):
    from sklearn.ensemble import IsolationForest
    assert not set(MODEL_FEATURES) & set(PROHIBITED_MODEL_INPUTS)
    hist = feat[feat.dataset == "HISTORICAL"]
    iso = IsolationForest(n_estimators=200, contamination=IF_CONTAMINATION,
                          random_state=IF_RANDOM_STATE).fit(hist[MODEL_FEATURES])
    raw_h = np.sort(-iso.score_samples(hist[MODEL_FEATURES]))

    def scores(d):
        raw = -iso.score_samples(d[MODEL_FEATURES])
        ml = np.searchsorted(raw_h, raw) / len(raw_h)                    # empirical CDF in [0,1]
        zmax = np.maximum(d.notional_zscore.abs(), d.quantity_zscore.abs())
        stat = np.minimum(zmax / 4.0, 1.0)
        ctx = np.minimum(1.0, 0.35 * d.is_pre_event
                         + 0.25 * np.minimum(np.maximum(d.volume_ratio - 1, 0) / 2, 1)
                         + 0.20 * np.minimum(d.time_deviation / 120, 1)
                         + 0.20 * (1 - np.minimum(d.trader_symbol_frequency / 0.10, 1)))
        comb = W_STAT * stat + W_ML * ml + W_CTX * ctx
        return stat, ml, ctx, comb, zmax

    out = feat.copy()
    out["statistical_score"], out["ml_score"], out["context_score"], out["combined_anomaly_score"], zmax = scores(out)
    thr_alert = float(np.quantile(out.loc[out.dataset == "HISTORICAL", "combined_anomaly_score"], 0.95))
    thr_high = float(np.quantile(out.loc[out.dataset == "HISTORICAL", "combined_anomaly_score"], 0.99))
    out["z_risk_level"] = np.where(zmax >= 3, "HIGH", np.where(zmax >= 2, "MEDIUM", "LOW"))   # project thresholds
    out["predicted_anomaly"] = out.combined_anomaly_score >= thr_alert
    out["risk_level"] = np.where(out.combined_anomaly_score >= thr_high, "HIGH",
                                 np.where(out.predicted_anomaly, "MEDIUM", "LOW"))
    test = out[out.dataset == "TEST"].copy()
    hist_ratio = hist.groupby("trader_id")["buy_sell_ratio"].mean()
    test["explanation"] = [
        explain(r, base1h[r.trader_id], base1d[r.trader_id], hist_ratio[r.trader_id]) if r.predicted_anomaly else ""
        for r in test.itertuples()]

    y, p = test.is_injected_anomaly.values, test.predicted_anomaly.values
    def metrics(tp, fp, tn, fn):
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        return pr, rc, (2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    tp, fp = int((y & p).sum()), int((~y & p).sum())
    tn, fn = int((~y & ~p).sum()), int((y & ~p).sum())
    rows = [dict(group="OVERALL", TP=tp, FP=fp, TN=tn, FN=fn, **dict(zip(["precision", "recall", "f1"], metrics(tp, fp, tn, fn))))]
    for at in ANOMALY_DISTRIBUTION:
        m = (test.anomaly_type == at).values
        tpa, fna = int((m & p).sum()), int((m & ~p).sum())
        rows.append(dict(group=at, TP=tpa, FP=fp, TN=tn, FN=fna,
                         **dict(zip(["precision", "recall", "f1"], metrics(tpa, fp, tn, fna)))))
    ev = pd.DataFrame(rows).round(4)
    return test, ev, thr_alert, thr_high


# =============================================================================
# VALIDATION
# =============================================================================
def validate_and_summarise(traders_df, sym_df, hist, test, events_out, feat, expected):
    allt = pd.concat([hist, test], ignore_index=True)
    key = ["trader_id", "symbol", "timestamp", "side", "quantity", "price"]
    ts = pd.to_datetime(allt["timestamp"], utc=True).dt.tz_convert(TZ)
    sec = ts.dt.hour * 3600 + ts.dt.minute * 60 + ts.dt.second
    sess = np.where(sec < 10 * 3600, "OPEN", np.where(sec < 15 * 3600, "MID_SESSION", "CLOSE"))
    checks = {
        "trade_id unique": allt.trade_id.is_unique,
        "trade_code unique": allt.trade_code.is_unique,
        "trade_code prefix == trader_id": bool((allt.trade_code.str.split("-").str[0] == allt.trader_id).all()),
        "quantity > 0": bool((allt.quantity > 0).all()),
        "price > 0": bool((allt.price > 0).all()),
        "notional > 0": bool((allt.notional_value > 0).all()),
        "notional == quantity x price": bool(np.allclose(allt.notional_value, allt.quantity * allt.price, atol=0.006)),
        "all trades within 09:15-15:30 IST": bool(((sec >= 9 * 3600 + 15 * 60) & (sec <= 15 * 3600 + 30 * 60)).all()),
        "market_session boundaries exact": bool((sess == allt.market_session.values).all()),
        "market_volume > 0": bool((feat.market_volume > 0).all()),
        "average_market_volume > 0": bool((feat.average_market_volume > 0).all()),
        "volume_ratio > 0": bool((feat.volume_ratio > 0).all()),
        "volume_ratio == mv/avg": bool(np.allclose(feat.volume_ratio, feat.market_volume / feat.average_market_volume, rtol=1e-4)),
        "volume_deviation == ratio-1": bool(np.allclose(feat.volume_deviation, feat.volume_ratio - 1, atol=1e-5)),
        "injected anomalies == NUM_ANOMALIES": int(test.is_injected_anomaly.sum()) == NUM_ANOMALIES,
        "normal test trades == NUM_TEST-NUM_ANOMALIES": int((~test.is_injected_anomaly).sum()) == NUM_TEST_TRADES - NUM_ANOMALIES,
        "historical injected anomalies == 0": int(hist.is_injected_anomaly.sum()) == 0,
        "feature rows == hist + test": len(feat) == NUM_HISTORICAL_TRADES + NUM_TEST_TRADES,
        "expected_anomalies rows == NUM_ANOMALIES": len(expected) == NUM_ANOMALIES,
        "events == NUM_MARKET_EVENTS": len(events_out) == NUM_MARKET_EVENTS,
        "no ground-truth in MODEL_FEATURES": not set(MODEL_FEATURES) & set(PROHIBITED_MODEL_INPUTS),
    }
    missing = int(sum(df.isna().sum().sum() for df in (traders_df, sym_df, hist, test, events_out, feat, expected)))
    stats = dict(
        traders=len(traders_df), symbols=len(sym_df), hist=len(hist), test=len(test),
        normal_test=int((~test.is_injected_anomaly).sum()), anomalies=int(test.is_injected_anomaly.sum()),
        events=len(events_out), feature_rows=len(feat), missing=missing,
        dup_records=int(allt.duplicated(subset=key).sum()),
        dup_ids=int(allt.trade_id.duplicated().sum()), dup_codes=int(allt.trade_code.duplicated().sum()),
        natural_unusual=int(hist.is_natural_unusual.sum()),
        trading_days=NUM_HISTORICAL_DAYS + NUM_TEST_DAYS)
    return checks, stats


def print_summary(checks, stats):
    print("\n========== DATA QUALITY CHECKS ==========")
    for k, v in checks.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print("\n========== DATASET SUMMARY ==========\n")
    print(f"Traders: {stats['traders']}")
    print(f"Symbols: {stats['symbols']}\n")
    print(f"Trading days: {stats['trading_days']}")
    print(f"Historical trades: {stats['hist']:,}")
    print(f"Test trades: {stats['test']:,}\n")
    print(f"Normal test trades: {stats['normal_test']}")
    print(f"Injected anomalies: {stats['anomalies']}\n")
    print(f"Market events: {stats['events']}\n")
    print(f"Feature rows: {stats['feature_rows']:,}\n")
    print(f"Naturally unusual historical trades (not injected): {stats['natural_unusual']}")
    print(f"Missing values: {stats['missing']}")
    print(f"Duplicate trade records: {stats['dup_records']}")
    print(f"Duplicate trade IDs: {stats['dup_ids']}")
    print(f"Duplicate trade codes: {stats['dup_codes']}\n")
    print("======================================")


# =============================================================================
# README
# =============================================================================
README = """# Synthetic Market Surveillance & Anomaly Detection Dataset

> This is a synthetic dataset created for an academic market-surveillance demonstration. The injected anomaly labels represent intentionally generated behavioral patterns and do not represent confirmed insider trading, actual market abuse, or real-world misconduct.

## 1. Purpose
Test bed for a cloud-based market-surveillance prototype that flags **statistically and behaviourally unusual trading for human review**. It supports trader profiling, Z-score detection, Isolation Forest, contextual (event/volume) detection, LOW/MEDIUM/HIGH risk classification, backend pipeline testing, a viva demo and evaluation against known synthetic anomalies. The system never claims to prove insider trading; alerts read *"Unusual trading activity detected. Further human review recommended."*

## 2. Synthetic nature
Everything is generated locally by `generate_dataset.py` with `numpy.random.default_rng(RANDOM_SEED)`. No real people, companies, prices, APIs or downloads. Same seed -> same dataset. Every row has `synthetic = True`.

## 3. Size (calculated from the generated files)
| Item | Count |
|---|---|
| Traders | {traders} |
| Symbols (fictional) | {symbols} |
| Trading days | {days} ({hist_days} historical + {test_days} test) |
| Historical trades | {hist:,} |
| Test trades | {test} ({normal_test} normal + {anomalies} injected anomalies) |
| Market events | {events} |
| Feature rows | {feature_rows:,} |
| Naturally unusual historical trades (`is_natural_unusual`, NOT injected) | {natural} |

## 4. Trader profiles
Six archetypes (Conservative, Active, Swing Trader, Momentum Trader, Sector-Focused, Diversified) are assigned at random to `TRD001..TRD050`. Each trader gets its own average quantity/notional and their std, trades per day, 2-6 preferred symbols (sector-focused traders: 2-3 sectors; diversified: distinct sectors), a preferred trading window and a BUY probability (about 30% of traders are strongly BUY- or SELL-skewed). So a Rs 10 lakh trade can be normal for one trader and extreme for another. `traders.csv` also stores the *realised* historical mean/std (`hist_*`).

## 5. Symbols
20 fictional companies across 12 sectors with different baseline price (Rs 100-4000), daily volatility (0.7%-3%), average daily volume and spread.

## 6. Historical trades
{hist:,} trades over {hist_days} business days. Trades are allocated to traders in proportion to their rates (largest-remainder). Day, symbol (about 96% preferred), time (about 90% inside the preferred window; the rest fall just outside with an exponential offset), side and quantity are drawn from the trader's own profile. Prices come from per-symbol minute-level price paths (`new = prev x (1 + N(0, vol))`, overnight gaps and event shocks); the executed price adds half the symbol spread. `notional_value = quantity x price` always. About 2% of rows are *naturally unusual* (larger quantity or off-window time) and flagged with `is_natural_unusual = True`; `is_injected_anomaly` stays False for them.

## 7. Test trades
{test} trades on the {test_days} trading days after the history: {normal_test} normal trades generated like the historical ones plus {anomalies} injected anomalies. Test days are short so the normal test density stays comparable with history.

## 8. Market events
{events} fictional events (`EARNINGS`, `MERGER`, ... ) with LOW/MEDIUM/HIGH severity. Every symbol has several; {test_events} events fall in the test window (an event-enriched window so contextual anomalies can be evaluated). Events create price shocks and volume spikes.

## 9. Market volume
Daily `market_volume` per symbol/day (log-normal noise, rare random spikes, event-day spikes). `average_market_volume` = mean of the **previous** up-to-20 trading days (day 0 uses the configured ADV). `volume_ratio = market_volume / average_market_volume`, `volume_deviation = volume_ratio - 1`. All four columns are in `feature_dataset.csv`.

## 10. Feature engineering
Frequency (1h / 1d, plus per-symbol 1d), rolling buy/sell ratio (last {bs_window} trades, `(buys+1)/(sells+1)`), `time_deviation` (minutes outside the preferred window, 0 inside), volume features, event features, price returns, smoothed `trader_symbol_frequency = (count+0.5)/(total+0.5x20)`, Z-scores.

## 11. Z-scores
`z = (x - mean) / std` using trader-specific history. Test trades use the frozen historical baseline; historical rows use an expanding **prior-only** baseline (z = 0 until {zmin} prior trades). If `std < 1e-6`, z = 0.

## 12. Isolation Forest inputs
`{model_features}`

Excluded: `price_return_after_trade`, `is_injected_anomaly`, `anomaly_type`, `expected_severity`. The Isolation Forest is fitted on historical rows only (`contamination={contam}`, `random_state={rs}` - project parameters, not universal truths).

## 13. Contextual features
`event_distance` (minutes to nearest event of that symbol), `is_pre_event` (within 24h before), `is_post_event` (within 24h after), volume features, `price_return_before_trade` (previous 60 trading minutes).

## 14. Anomaly injection (exactly {anomalies})
| Type | Count | How |
|---|---|---|
{dist_rows}

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
- The test window is short ({test_days} days) and event-enriched.
- Detection results depend on the injected patterns and project thresholds.

## 21. Regenerate
```
pip install numpy pandas scikit-learn
python generate_dataset.py
```
Change the constants at the top of the script (seed, sizes, anomaly counts) and re-run.
"""


def write_readme(stats):
    dist_rows = "\n".join(f"| {k} | {v} | see below |" for k, v in ANOMALY_DISTRIBUTION.items())
    text = README.format(
        traders=stats["traders"], symbols=stats["symbols"], days=stats["trading_days"],
        hist_days=NUM_HISTORICAL_DAYS, test_days=NUM_TEST_DAYS, hist=stats["hist"],
        test=stats["test"], normal_test=stats["normal_test"], anomalies=stats["anomalies"],
        events=stats["events"], feature_rows=stats["feature_rows"], natural=stats["natural_unusual"],
        test_events=NUM_TEST_EVENTS, bs_window=BUY_SELL_WINDOW, zmin=Z_MIN_HISTORY,
        model_features=", ".join(MODEL_FEATURES), contam=IF_CONTAMINATION, rs=IF_RANDOM_STATE,
        dist_rows=dist_rows)
    with open("DATASET_README.md", "w", encoding="utf-8") as f:
        f.write(text)


# =============================================================================
# MAIN
# =============================================================================
def main():
    validate_config()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ---- calendar -----------------------------------------------------------------
    n_days = NUM_HISTORICAL_DAYS + NUM_TEST_DAYS
    dates = pd.bdate_range(START_DATE, periods=n_days)
    W.update(n_days=n_days, dates=dates, dates_np=dates.values.astype("datetime64[ns]"),
             ord_days=np.array([d.toordinal() for d in dates], dtype=np.int64))

    # ---- symbols, events, prices, volumes --------------------------------------------
    sym_df = build_symbols()
    W.update(ns=len(sym_df), symbols=sym_df.symbol.values, sectors=sym_df.sector.values,
             base_price=sym_df.baseline_price.values, spread=sym_df.typical_spread.values)
    events = build_events(sym_df, dates)
    W["P"] = build_price_paths(sym_df, events)
    W["day_move"] = np.array([np.mean(np.abs(W["P"][:, d * MIN_PER_DAY + 375] / W["P"][:, d * MIN_PER_DAY] - 1))
                              for d in range(n_days)])
    W["mv"], W["avg_mv"] = build_volumes(sym_df, events)

    # ---- traders & historical trades ----------------------------------------------------
    traders = build_traders(sym_df)
    rates = np.array([t["rate"] for t in traders])
    hist_counts = alloc(NUM_HISTORICAL_TRADES, rates)
    test_counts = alloc(NUM_TEST_TRADES - NUM_ANOMALIES, rates)
    hist = finalize(gen_normal_trades(traders, hist_counts, (0, NUM_HISTORICAL_DAYS), "HISTORICAL", True))

    # trader baselines from history
    stats = {}
    g = hist.groupby("trader_id")
    for t in traders:
        h = hist[hist.trader_id == t["trader_id"]]
        counts = np.bincount(h.sym_idx.values, minlength=W["ns"])
        stats[t["trader_id"]] = dict(mean_q=h.quantity.mean(), std_q=h.quantity.std(),
                                     mean_n=h.notional_value.mean(), std_n=h.notional_value.std(),
                                     n=len(h), counts=counts)

    # ---- test trades (normal + injected) -------------------------------------------------
    normal_test = gen_normal_trades(traders, test_counts, (NUM_HISTORICAL_DAYS, n_days), "TEST", False)
    anomalies = inject_anomalies(traders, stats, events)
    assert len(anomalies) == NUM_ANOMALIES, f"anomaly count mismatch: {len(anomalies)}"
    test = finalize(pd.concat([normal_test, anomalies], ignore_index=True))
    assert len(test) == NUM_TEST_TRADES

    # ---- ids / codes ----------------------------------------------------------------------
    hist = hist.sort_values(["ts_abs"], kind="stable").reset_index(drop=True)
    test = test.sort_values(["ts_abs"], kind="stable").reset_index(drop=True)
    hist["trade_id"] = np.arange(1, len(hist) + 1)
    test["trade_id"] = np.arange(len(hist) + 1, len(hist) + len(test) + 1)
    allt = pd.concat([hist, test], ignore_index=True)
    allt["trade_code"] = [f"{tr}-{n:06d}" for tr, n in zip(allt.trader_id, allt.groupby("trader_id").cumcount() + 1)]
    hist, test = allt[allt.dataset == "HISTORICAL"].copy(), allt[allt.dataset == "TEST"].copy()

    # ---- features -------------------------------------------------------------------------
    feat, base1h, base1d = build_features(allt, traders, events)

    # ---- tables to write ----------------------------------------------------------------
    trade_cols = ["trade_id", "trade_code", "trader_id", "symbol", "side", "quantity", "price",
                  "notional_value", "timestamp", "trade_date", "trade_time", "sector", "market_session",
                  "synthetic", "is_injected_anomaly", "anomaly_type", "is_natural_unusual"]
    hist_out, test_out = hist[trade_cols].reset_index(drop=True), test[trade_cols].reset_index(drop=True)

    sym_out = sym_df.copy()
    ev_out = events[["event_id", "symbol", "event_type", "event_timestamp", "event_severity", "description"]]

    hs = hist.groupby("trader_id")
    tr_rows = []
    for t in traders:
        tid = t["trader_id"]
        tr_rows.append(dict(
            trader_id=tid, trader_type=t["type"],
            average_trade_quantity=round(t["avg_q"], 1), quantity_std=round(t["q_std"], 2),
            average_notional=round(t["avg_notional"], 2), notional_std=round(t["notional_std"], 2),
            normal_trades_per_day=round(hist_counts[t["idx"]] / NUM_HISTORICAL_DAYS, 2),
            preferred_symbols=";".join(W["symbols"][t["pref_idx"]]),
            preferred_sectors=";".join(t["pref_sectors"]),
            preferred_start_time=hhmm(t["ws"]), preferred_end_time=hhmm(t["we"]),
            buy_probability=round(t["buy_prob"], 3),
            hist_mean_quantity=round(stats[tid]["mean_q"], 2), hist_std_quantity=round(stats[tid]["std_q"], 2),
            hist_mean_notional=round(stats[tid]["mean_n"], 2), hist_std_notional=round(stats[tid]["std_n"], 2),
            hist_trade_count=stats[tid]["n"]))
    traders_out = pd.DataFrame(tr_rows)

    feature_cols = (["trade_id", "trader_id", "symbol", "quantity", "price", "notional_value",
                     "trade_frequency_1h", "trade_frequency_1d", "buy_sell_ratio", "time_deviation",
                     "market_volume", "average_market_volume", "volume_ratio", "volume_deviation",
                     "price_return_before_trade", "price_return_after_trade",
                     "event_distance", "is_pre_event", "is_post_event", "trader_symbol_frequency",
                     "notional_zscore", "quantity_zscore",
                     "is_injected_anomaly", "anomaly_type", "expected_severity"]
                    + ["trade_code", "dataset", "timestamp", "is_natural_unusual", "trade_frequency_symbol_1d",
                       "signal_A", "signal_B", "signal_C", "signal_D", "signal_E", "signal_F", "signal_count"])
    feat_out = feat[feature_cols].sort_values("trade_id").reset_index(drop=True)

    inj = test[test.is_injected_anomaly].merge(feat[["trade_id", "expected_severity"]], on="trade_id")
    expected = inj[["trade_id", "trade_code", "trader_id", "anomaly_type", "expected_severity"]] \
        .sort_values("trade_id").reset_index(drop=True)

    # ---- validate, write ----------------------------------------------------------------
    checks, st = validate_and_summarise(traders_out, sym_out, hist_out, test_out, ev_out, feat_out, expected)
    for name, df in [("traders", traders_out), ("symbols", sym_out), ("historical_trades", hist_out),
                     ("test_trades", test_out), ("market_events", ev_out),
                     ("expected_anomalies", expected), ("feature_dataset", feat_out)]:
        df.to_csv(os.path.join(OUTPUT_DIR, f"{name}.csv"), index=False)
    write_readme(st)
    print_summary(checks, st)
    if not all(checks.values()):
        print("WARNING: some checks failed", file=sys.stderr)

    # ---- severity distribution & reference detector ---------------------------------------
    print("\nExpected severity of injected anomalies:")
    print(expected.expected_severity.value_counts().to_string())
    print("\nSeverity by anomaly type:")
    print(pd.crosstab(expected.anomaly_type, expected.expected_severity).to_string())
    try:
        test_res, ev, thr_alert, thr_high = run_reference_detector(feat, base1h, base1d)
        keep = ["trade_id", "trade_code", "trader_id", "symbol", "is_injected_anomaly", "anomaly_type",
                "expected_severity", "statistical_score", "ml_score", "context_score",
                "combined_anomaly_score", "z_risk_level", "risk_level", "predicted_anomaly", "explanation"]
        test_res[keep].sort_values("trade_id").round(4).to_csv(
            os.path.join(OUTPUT_DIR, "reference_detection_results.csv"), index=False)
        ev.to_csv(os.path.join(OUTPUT_DIR, "reference_evaluation.csv"), index=False)
        print(f"\nReference detector (alert threshold = hist p95 of combined score = {thr_alert:.3f}; "
              f"HIGH >= hist p99 = {thr_high:.3f})")
        print(ev.to_string(index=False))
    except ImportError:
        print("\nscikit-learn not installed - skipping the optional reference detector.")


if __name__ == "__main__":
    main()