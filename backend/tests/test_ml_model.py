from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml_model import (
    PROJECT_ROOT,
    ModelTrainingError,
    _is_contained,
    _normalize_borrower_id,
    _normalize_loan_decision,
    _normalize_risk_label,
    _risk_from_decision_and_score,
    _safe_to_numeric,
    _yes_no_to_bool,
    available_datasets,
    model_is_trained,
    resolve_dataset_key,
    resolve_dataset_path,
)


@pytest.mark.parametrize("value", ["yes", "YES", " Yes ", "true", "True", "1", True])
def test_affirmative_values_become_true(value):
    assert _yes_no_to_bool(value) is True


@pytest.mark.parametrize("value", ["no", "NO", " No ", "false", "False", "0", False])
def test_negative_values_become_false(value):
    assert _yes_no_to_bool(value) is False


@pytest.mark.parametrize("value", ["maybe", "", "unknown", np.nan, None])
def test_unreadable_values_become_none(value):
    assert _yes_no_to_bool(value) is None


def test_borrower_ids_are_normalised():
    assert _normalize_borrower_id("  b-102 ") == "B-102"
    assert _normalize_borrower_id(102) == "102"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("low", "low"),
        ("Low Risk", "low"),
        ("  MEDIUM  ", "medium"),
        ("High Risk", "high"),
    ],
)
def test_risk_labels_are_normalised(raw, expected):
    assert _normalize_risk_label(raw) == expected


@pytest.mark.parametrize("raw", ["very low", "", "unknown", np.nan])
def test_an_unrecognised_risk_label_is_dropped(raw):
    assert _normalize_risk_label(raw) is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("approved", "approved"),
        ("Approve", "approved"),
        ("Conditionally Approved", "conditionally_approved"),
        ("conditional", "conditionally_approved"),
        ("Under Review", "under_review"),
        ("rejected", "rejected"),
        ("declined", "rejected"),
    ],
)
def test_loan_decisions_are_normalised(raw, expected):
    assert _normalize_loan_decision(raw) == expected


def test_an_unknown_decision_defaults_to_review_not_approval():
    assert _normalize_loan_decision("pending paperwork") == "under_review"
    assert _normalize_loan_decision("") == "under_review"


def test_an_approval_with_a_healthy_score_is_low_risk():
    assert _risk_from_decision_and_score("approved", 750) == "low"


def test_an_approval_with_a_poor_score_is_not_low_risk():
    assert _risk_from_decision_and_score("approved", 580) == "medium"


def test_a_rejection_is_always_high_risk():
    assert _risk_from_decision_and_score("rejected", 800) == "high"
    assert _risk_from_decision_and_score("rejected", 400) == "high"


@pytest.mark.parametrize(
    "score,expected", [(800, "low"), (700, "medium"), (500, "high")]
)
def test_a_conditional_approval_is_graded_by_score(score, expected):
    assert _risk_from_decision_and_score("conditionally approved", score) == expected


def test_a_missing_score_still_grades():
    assert _risk_from_decision_and_score("approved", None) == "low"
    assert _risk_from_decision_and_score("under review", np.nan) == "medium"


def test_non_numeric_values_become_missing_not_errors():
    result = _safe_to_numeric(pd.Series(["12", "not-a-number", "3.5", ""]))

    assert result.tolist()[0] == 12
    assert pd.isna(result.tolist()[1])
    assert result.tolist()[2] == 3.5


def test_a_path_inside_the_root_is_contained(tmp_path):
    (tmp_path / "inside.csv").write_text("a,b\n1,2", encoding="utf-8")

    assert _is_contained(tmp_path / "inside.csv", tmp_path) is True


def test_a_path_outside_the_root_is_not_contained(tmp_path):
    assert _is_contained(Path("/etc/passwd"), tmp_path) is False
    assert _is_contained(tmp_path / ".." / "outside.csv", tmp_path) is False


def test_the_root_itself_is_contained(tmp_path):
    assert _is_contained(tmp_path, tmp_path) is True


def test_every_listed_dataset_exists_and_is_a_file():
    for name, path in available_datasets().items():
        assert path.is_file()
        assert path.name == name


def test_dataset_keys_are_names_not_paths():
    for name in available_datasets():
        assert "/" not in name
        assert "\\" not in name
        assert not name.startswith("~$")


def test_every_listed_dataset_lives_under_the_project_root():
    for path in available_datasets().values():
        assert _is_contained(path, PROJECT_ROOT)


def test_a_known_key_resolves_to_its_file():
    registry = available_datasets()
    if not registry:
        pytest.skip("no datasets are present in this checkout")

    name = sorted(registry)[0]
    assert resolve_dataset_key(name) == registry[name]


@pytest.mark.parametrize(
    "probe",
    [
        "/etc/passwd",
        "C:/Windows/win.ini",
        "../../../../etc/passwd",
        "....//....//etc/passwd",
        "../1000bor.csv",
        "1000bor.csv/../../secret",
    ],
)
def test_a_traversal_probe_is_refused_by_the_allowlist(probe):
    with pytest.raises(ModelTrainingError, match="Unknown dataset"):
        resolve_dataset_key(probe)


def test_the_rejection_does_not_echo_a_filesystem_path():
    with pytest.raises(ModelTrainingError) as raised:
        resolve_dataset_key("/etc/passwd")

    message = str(raised.value)
    assert "not found at" not in message
    assert str(PROJECT_ROOT) not in message


def test_the_rejection_names_the_permitted_datasets():
    with pytest.raises(ModelTrainingError) as raised:
        resolve_dataset_key("nonexistent.csv")

    assert "Available datasets" in str(raised.value)


def test_a_path_outside_the_root_is_refused_even_on_the_trusted_path():
    with pytest.raises(ModelTrainingError):
        resolve_dataset_path(Path("/etc/passwd"))


def test_model_is_trained_reports_a_boolean():
    assert isinstance(model_is_trained(), bool)


def test_predicting_without_a_model_is_a_clear_error(monkeypatch):
    from app import ml_model

    monkeypatch.setattr(ml_model, "MODEL_PATH", Path("/nonexistent/model.joblib"))

    with pytest.raises(Exception) as raised:
        ml_model.predict_risk({"monthly_income_inr": 50000})

    assert "train" in str(raised.value).lower() or "model" in str(raised.value).lower()
