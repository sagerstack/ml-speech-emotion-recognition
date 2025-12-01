"""Unit tests for the prediction buffer used by Evidently monitoring."""

from datetime import datetime, timedelta

from app.services.prediction_buffer import PredictionBuffer, PredictionRecord


def _record(ts: datetime, version: str = "1") -> PredictionRecord:
    return PredictionRecord(
        timestamp=ts,
        model_version=version,
        predicted_emotion="happy",
        confidence=0.9,
        probabilities={"happy": 0.9, "sad": 0.1},
        features={"feature_a": 0.5, "feature_b": 1.2},
        actual_emotion="happy",
        filename="sample.wav",
    )


def test_add_and_stats_track_versions_and_latest_timestamp():
    buffer = PredictionBuffer(max_records=2)

    now = datetime.utcnow()
    first_len = buffer.add(_record(now, version="1"))
    second_len = buffer.add(_record(now + timedelta(seconds=1), version="2"))

    assert first_len == 1
    assert second_len == 2

    stats = buffer.stats()
    assert stats["total_records"] == 2
    assert stats["by_version"] == {"1": 1, "2": 1}
    assert stats["max_records"] == 2
    assert stats["latest_timestamp"] is not None


def test_to_dataframe_includes_features_and_probabilities():
    buffer = PredictionBuffer(max_records=3)
    buffer.add(_record(datetime.utcnow()))

    df = buffer.to_dataframe()

    assert set(["feature_a", "feature_b"]).issubset(df.columns)
    assert set(["proba_happy", "proba_sad"]).issubset(df.columns)
    assert df.iloc[0]["predicted_emotion"] == "happy"
    assert df.iloc[0]["confidence"] == 0.9
