"""Tests for tolerating a non-`Date` index column in stockstats_utils (#890).

Guards against a download frame whose date column is `index` or `Datetime`
instead of `Date`, which would otherwise silently drop every indicator.
"""

from __future__ import annotations

import pandas as pd
import pytest

from tradingagents.dataflows import stockstats_utils as su


def _ohlcv(date_col: str) -> pd.DataFrame:
    """OHLCV frame whose date column is named `date_col`."""
    dates = pd.bdate_range("2026-04-01", periods=10)
    return pd.DataFrame({
        date_col: dates,
        "Open": [100.0 + i for i in range(10)],
        "High": [101.0 + i for i in range(10)],
        "Low": [99.0 + i for i in range(10)],
        "Close": [100.5 + i for i in range(10)],
        "Volume": [1_000_000 + i for i in range(10)],
    })


@pytest.mark.unit
class TestEnsureDateColumn:
    def test_renames_index_column(self):
        out = su._ensure_date_column(_ohlcv("index"))
        assert "Date" in out.columns and "index" not in out.columns

    def test_renames_datetime_and_date_variants(self):
        assert "Date" in su._ensure_date_column(_ohlcv("Datetime")).columns
        assert "Date" in su._ensure_date_column(_ohlcv("date")).columns

    def test_leaves_existing_date_untouched(self):
        df = _ohlcv("Date")
        assert su._ensure_date_column(df) is df  # no-op short-circuit

    def test_no_datelike_column_is_left_alone(self):
        df = pd.DataFrame({"Close": [1, 2, 3]})
        out = su._ensure_date_column(df)
        assert "Date" not in out.columns  # nothing to rename; caller handles


@pytest.mark.unit
class TestCleanDataframeAcrossVersions:
    def test_clean_handles_index_column(self):
        """A frame with `index` instead of `Date` must still clean to a
        usable, date-parsed frame (was KeyError: 'Date')."""
        cleaned = su._clean_dataframe(_ohlcv("index"))
        assert "Date" in cleaned.columns
        assert pd.api.types.is_datetime64_any_dtype(cleaned["Date"])
        assert len(cleaned) == 10

    def test_clean_handles_legacy_date_column(self):
        cleaned = su._clean_dataframe(_ohlcv("Date"))
        assert len(cleaned) == 10

    def test_clean_removes_timezone_from_date_column(self):
        """带时区的 Date 列必须先去时区，后续才能和无时区 Timestamp 比较。"""
        df = _ohlcv("Date")
        df["Date"] = pd.date_range(
            "2026-04-01 09:30:00",
            periods=10,
            freq="B",
            tz="America/New_York",
        )

        cleaned = su._clean_dataframe(df)

        assert len(cleaned) == 10
        assert cleaned["Date"].dt.tz is None

    def test_indicators_compute_after_index_rename(self):
        """stockstats must compute indicators on a frame whose date column
        arrived as `index`, instead of erroring per indicator."""
        from stockstats import wrap
        cleaned = su._clean_dataframe(_ohlcv("index"))
        df = wrap(cleaned)
        df["close_5_sma"]  # triggers calculation
        assert "close_5_sma" in df.columns
        assert df["close_5_sma"].notna().any()


@pytest.mark.unit
class TestTimezoneNormalization:
    def test_normalize_market_timestamps_accepts_mixed_timezone_values(self):
        """混合时区与无时区值时，也要能统一落成无时区时间。"""
        values = pd.Series(
            [
                pd.Timestamp("2026-04-01 09:30:00"),
                pd.Timestamp("2026-04-02 09:30:00", tz="America/New_York"),
                "2026-04-03 09:30:00+00:00",
            ]
        )

        dates = su._normalize_market_timestamps(values)

        assert len(dates) == 3
        assert dates.dt.tz is None

    def test_coerce_ohlcv_dates_drops_timezone_from_index(self):
        """带时区的索引也要先归一化，否则 stale guard 会比较失败。"""
        data = pd.DataFrame(
            {"Close": [100.5, 101.5]},
            index=pd.DatetimeIndex(
                [
                    pd.Timestamp("2026-04-01 09:30:00", tz="America/New_York"),
                    pd.Timestamp("2026-04-02 09:30:00", tz="America/New_York"),
                ],
                name="Date",
            ),
        )

        dates = su._coerce_ohlcv_dates(data)

        assert len(dates) == 2
        assert dates.dt.tz is None
