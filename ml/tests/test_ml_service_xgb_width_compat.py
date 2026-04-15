import numpy as np

from ml.serving import ml_service


class _FakeEstimator:
    def __init__(self, width: int):
        self.n_features_in_ = width


class _FakeWrappedModel:
    def __init__(self, width: int):
        self.model = _FakeEstimator(width)


class _FakeDirectModel:
    def __init__(self, width: int):
        self.n_features_in_ = width


def test_legacy_xgb_width_is_compatible(monkeypatch):
    monkeypatch.setattr(ml_service, "xgb_model", _FakeWrappedModel(21))
    assert ml_service._xgb_model_width_compatible() is True


def test_runtime_xgb_width_is_compatible(monkeypatch):
    monkeypatch.setattr(
        ml_service,
        "xgb_model",
        _FakeWrappedModel(ml_service.RUNTIME_XGB_FEATURE_WIDTH),
    )
    assert ml_service._xgb_model_width_compatible() is True


def test_align_xgb_features_truncates_to_expected_width(monkeypatch):
    monkeypatch.setattr(ml_service, "xgb_model", _FakeWrappedModel(21))
    features = np.arange(26, dtype=np.float64).reshape(1, 26)

    aligned = ml_service._align_xgb_features(features)

    assert aligned.shape == (1, 21)
    assert np.array_equal(aligned, features[:, :21])


def test_align_xgb_features_pads_to_expected_width(monkeypatch):
    monkeypatch.setattr(ml_service, "xgb_model", _FakeWrappedModel(26))
    features = np.arange(21, dtype=np.float64).reshape(1, 21)

    aligned = ml_service._align_xgb_features(features)

    assert aligned.shape == (1, 26)
    assert np.array_equal(aligned[:, :21], features)
    assert np.count_nonzero(aligned[:, 21:]) == 0


def test_expected_width_from_direct_estimator(monkeypatch):
    monkeypatch.setattr(ml_service, "xgb_model", _FakeDirectModel(21))
    assert ml_service._xgb_expected_width() == 21
