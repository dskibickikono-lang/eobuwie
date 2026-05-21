import sys
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

# ── STREAMLIT MOCK (must happen before importing the app) ──────────────────────
_mock_st = MagicMock()
_mock_st.session_state = MagicMock()
_mock_st.session_state.__contains__ = MagicMock(return_value=False)

# Prevent form-submit / button blocks from executing during import
_mock_st.form_submit_button.return_value = False
_mock_st.button.return_value = False
_mock_st.file_uploader.return_value = None

# Fix unpacking: st.columns(n) → list of n mocks; st.tabs([...]) → list of mocks
_mock_st.columns.side_effect = lambda n: [
    MagicMock() for _ in (range(n) if isinstance(n, int) else range(len(n)))
]
_mock_st.tabs.side_effect = lambda labels: [MagicMock() for _ in labels]

sys.modules["streamlit"] = _mock_st
sys.path.insert(0, ".")
import eobuwie_app as app  # noqa: E402  (import after mock)


# ── KPI CONSTANTS ──────────────────────────────────────────────────────────────
def test_pick_target_is_460():
    assert app.PICK_TARGET == 460


def test_pack_target_is_464():
    assert app.PACK_TARGET == 464


# ── COLOR-STATUS THRESHOLDS ────────────────────────────────────────────────────
@pytest.mark.parametrize("val,expected_hex", [
    (1.00, "#064e3b"),   # dark green – 100%
    (0.94, "#064e3b"),   # dark green – exact lower boundary
    (0.93, "#059669"),   # light green – just below 94%
    (0.80, "#059669"),   # light green – exact lower boundary
    (0.79, "#b45309"),   # amber – just below 80%
    (0.50, "#b45309"),   # amber – exact lower boundary
    (0.49, "#7f1d1d"),   # red   – just below 50%
    (0.00, "#7f1d1d"),   # red   – zero
])
def test_color_thresholds(val, expected_hex):
    assert expected_hex in app.get_color_status(val)


def test_color_status_nan_is_empty():
    assert app.get_color_status(float("nan")) == ""


def test_color_status_string_is_empty():
    assert app.get_color_status("TRAINING") == ""


def test_color_status_nb_is_empty():
    assert app.get_color_status("NB") == ""


# ── TREND FORMATTER ────────────────────────────────────────────────────────────
def test_format_trend_positive_above_5pct():
    assert "🟢" in app.format_trend(0.06)


def test_format_trend_negative_below_minus5pct():
    assert "🔴" in app.format_trend(-0.06)


def test_format_trend_neutral_small_change():
    assert "⚪" in app.format_trend(0.02)


def test_format_trend_nan_returns_grey():
    assert app.format_trend(float("nan")) == "⚪"


# ── BULK UPLOAD PARSER (melt + coerce) ────────────────────────────────────────
class TestBulkParser:
    """Simulates the wide-format CSV import with dirty production values."""

    DIRTY_DF = pd.DataFrame({
        "login":      ["OT00001", "OT00002", "OT00003"],
        "2024-01-01": [350,       "SZKOLENIA", 200],
        "2024-01-02": ["NB",      420,          "L4"],
        "2024-01-03": [460,       410,           None],
    })
    DATE_COLS = ["2024-01-01", "2024-01-02", "2024-01-03"]

    def _melt(self, df=None):
        df = df if df is not None else self.DIRTY_DF.copy()
        melted = pd.melt(
            df,
            id_vars=["login"],
            value_vars=self.DATE_COLS,
            var_name="Date",
            value_name="Units_per_Shift",
        )
        melted.rename(columns={"login": "Worker_ID"}, inplace=True)
        melted["Department"] = "PICK"
        melted["Units_per_Shift"] = pd.to_numeric(melted["Units_per_Shift"], errors="coerce")
        return melted[["Worker_ID", "Department", "Date", "Units_per_Shift"]]

    def test_melt_row_count(self):
        assert len(self._melt()) == 9  # 3 workers × 3 dates

    def test_dirty_strings_become_nan(self):
        result = self._melt()
        assert result["Units_per_Shift"].isna().sum() == 4  # SZKOLENIA, NB, L4, None

    def test_valid_numerics_preserved(self):
        result = self._melt()
        valid = result["Units_per_Shift"].dropna()
        assert len(valid) == 5
        assert 460.0 in valid.values

    def test_szkolenia_does_not_crash_pipeline(self):
        result = app.clean_and_aggregate_data(self._melt())
        assert not result.empty

    def test_l4_does_not_crash_pipeline(self):
        df = pd.DataFrame({
            "login": ["OT00004"],
            "2024-01-01": ["L4"],
            "2024-01-02": [460],
        })
        date_cols = ["2024-01-01", "2024-01-02"]
        melted = pd.melt(df, id_vars=["login"], value_vars=date_cols,
                         var_name="Date", value_name="Units_per_Shift")
        melted.rename(columns={"login": "Worker_ID"}, inplace=True)
        melted["Department"] = "PICK"
        melted["Units_per_Shift"] = pd.to_numeric(melted["Units_per_Shift"], errors="coerce")
        melted = melted[["Worker_ID", "Department", "Date", "Units_per_Shift"]]
        result = app.clean_and_aggregate_data(melted)
        assert not result.empty
        assert result["Units_per_Shift"].isna().sum() == 0

    def test_id_column_detection_login(self):
        df = pd.DataFrame({"login": ["OT001"], "2024-01-01": [300]})
        id_col = next((c for c in df.columns if str(c).strip().lower() in ["login", "worker_id", "worker id"]), None)
        assert id_col == "login"

    def test_id_column_detection_worker_id(self):
        df = pd.DataFrame({"Worker_ID": ["OT001"], "2024-01-01": [300]})
        id_col = next((c for c in df.columns if str(c).strip().lower() in ["login", "worker_id", "worker id"]), None)
        assert id_col == "Worker_ID"

    def test_date_column_detection_via_to_datetime(self):
        columns = ["login", "2024-01-01", "2024-01-02", "2024-01-03"]
        date_cols = []
        for col in columns:
            try:
                pd.to_datetime(str(col))
                date_cols.append(col)
            except (ValueError, TypeError):
                continue
        assert "2024-01-01" in date_cols
        assert "login" not in date_cols

    def test_all_dirty_worker_returns_empty_agg(self):
        df = pd.DataFrame({
            "Worker_ID":         ["OT99999", "OT99999"],
            "Department":        ["PICK", "PICK"],
            "Date":              pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "Units_per_Shift":   ["SZKOLENIA", "NB"],
        })
        result = app.clean_and_aggregate_data(df)
        assert result.empty


# ── CLEAN AND AGGREGATE ────────────────────────────────────────────────────────
class TestCleanAndAggregate:
    def _base(self):
        return pd.DataFrame({
            "Worker_ID":        ["OT001", "OT001", "OT002"],
            "Department":       ["PICK",  "PICK",  "PICK"],
            "Date":             pd.to_datetime(["2024-01-01", "2024-01-08", "2024-01-01"]),
            "Units_per_Shift":  [460, 400, 230],
        })

    def test_week_column_created(self):
        assert "Week" in app.clean_and_aggregate_data(self._base()).columns

    def test_week_values_prefixed_w(self):
        result = app.clean_and_aggregate_data(self._base())
        assert all(str(w).startswith("w") for w in result["Week"])

    def test_nan_units_dropped_from_output(self):
        df = self._base().astype({"Units_per_Shift": object})
        df.loc[0, "Units_per_Shift"] = "NB"
        result = app.clean_and_aggregate_data(df)
        assert result["Units_per_Shift"].isna().sum() == 0

    def test_groupby_computes_mean(self):
        df = pd.DataFrame({
            "Worker_ID":       ["OT001", "OT001"],
            "Department":      ["PICK",  "PICK"],
            "Date":            pd.to_datetime(["2024-01-01", "2024-01-03"]),
            "Units_per_Shift": [400, 460],
        })
        result = app.clean_and_aggregate_data(df)
        # Both dates fall in the same ISO week → mean = 430
        assert len(result) == 1
        assert abs(result["Units_per_Shift"].iloc[0] - 430.0) < 0.001


# ── PROCESS DEPARTMENT DATA ────────────────────────────────────────────────────
class TestProcessDepartmentData:
    def _agg(self):
        return pd.DataFrame({
            "Worker_ID":       ["OT001", "OT001", "OT002", "OT002"],
            "Department":      ["PICK",  "PICK",  "PICK",  "PICK"],
            "Week":            ["w1",    "w2",    "w1",    "w2"],
            "Units_per_Shift": [460.0,   400.0,   220.0,   300.0],
        })

    def test_pct_of_target_at_full_output(self):
        result, weeks = app.process_department_data(self._agg(), "PICK", 460)
        val = result.loc[result["Worker_ID"] == "OT001", "w1"].values[0]
        assert abs(val - 1.0) < 0.001

    def test_critical_worker_below_50pct(self):
        result, _ = app.process_department_data(self._agg(), "PICK", 460)
        val = result.loc[result["Worker_ID"] == "OT002", "w1"].values[0]
        assert val < 0.50

    def test_trend_wow_column_present(self):
        result, _ = app.process_department_data(self._agg(), "PICK", 460)
        assert "Trend (W-o-W)" in result.columns

    def test_avg_efficiency_column_present(self):
        result, _ = app.process_department_data(self._agg(), "PICK", 460)
        assert "Avg Efficiency" in result.columns

    def test_sorted_ascending_by_latest_week(self):
        result, weeks = app.process_department_data(self._agg(), "PICK", 460)
        latest_vals = result[weeks[-1]].dropna().tolist()
        assert latest_vals == sorted(latest_vals)

    def test_wrong_dept_returns_empty(self):
        result, weeks = app.process_department_data(self._agg(), "PACK", 464)
        assert result.empty
        assert weeks == []

    def test_pack_target_applied_correctly(self):
        df = pd.DataFrame({
            "Worker_ID":       ["OT050"],
            "Department":      ["PACK"],
            "Week":            ["w1"],
            "Units_per_Shift": [464.0],
        })
        result, _ = app.process_department_data(df, "PACK", 464)
        val = result.loc[result["Worker_ID"] == "OT050", "w1"].values[0]
        assert abs(val - 1.0) < 0.001


# ── MOCK DATA GENERATOR ────────────────────────────────────────────────────────
def test_mock_data_has_required_columns():
    df = app.generate_mock_data()
    assert set(["Worker_ID", "Department", "Date", "Units_per_Shift"]).issubset(df.columns)


def test_mock_data_departments_only_pick_and_pack():
    df = app.generate_mock_data()
    assert set(df["Department"].unique()).issubset({"PICK", "PACK"})


# ── SECURITY & VALIDATION ──────────────────────────────────────────────────────
class TestSecurityValidation:
    @pytest.mark.parametrize("w_id,expected", [
        ("OT00123", True),
        ("ot00123", True),
        ("A1", True),
        ("VERYLONGID12345", True),
        ("A", False),            # Too short
        ("TOOLONGID1234567", False), # Too long (16 chars)
        ("OT@123", False),       # Special char
        ("OT 123", False),       # Space
        ("OT;DROP", False),      # Potential SQLi attempt
        ("NAN", False),          # Null artifact
        ("NONE", False),         # Null artifact
        ("", False),             # Empty
        (None, False),           # None
        (123, False),            # Not a string
    ])
    def test_is_valid_worker_id(self, w_id, expected):
        assert app.is_valid_worker_id(w_id) == expected
