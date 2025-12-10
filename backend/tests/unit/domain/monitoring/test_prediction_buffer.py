"""Unit tests for the prediction buffer used by Evidently monitoring."""

from datetime import datetime, timedelta

import pytest

from app.domain.monitoring.prediction_buffer import PredictionBuffer, PredictionRecord


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


@pytest.mark.unit
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


@pytest.mark.unit
def test_to_dataframe_includes_features_and_probabilities():
    buffer = PredictionBuffer(max_records=3)
    buffer.add(_record(datetime.utcnow()))

    df = buffer.to_dataframe()

    assert set(["feature_a", "feature_b"]).issubset(df.columns)
    assert set(["proba_happy", "proba_sad"]).issubset(df.columns)
    assert df.iloc[0]["predicted_emotion"] == "happy"
    assert df.iloc[0]["confidence"] == 0.9


@pytest.mark.unit
def test_update_feedback_success():
    """Test updating feedback for existing prediction."""
    buffer = PredictionBuffer(max_records=10)
    now = datetime.utcnow()

    record = PredictionRecord(
        timestamp=now,
        model_version="1",
        predicted_emotion="happy",
        confidence=0.9,
        probabilities={"happy": 0.9, "sad": 0.1},
        features={"feature_a": 0.5},
        actual_emotion=None,
        filename="test.wav",
    )
    buffer.add(record)

    # Update with actual emotion
    result = buffer.update_feedback(record.prediction_id, "sad")

    assert result is True
    assert record.actual_emotion == "sad"


@pytest.mark.unit
def test_update_feedback_not_found():
    """Test updating feedback for non-existent prediction."""
    buffer = PredictionBuffer(max_records=10)
    buffer.add(_record(datetime.utcnow()))

    # Try to update non-existent prediction
    result = buffer.update_feedback("non-existent-id", "sad")

    assert result is False


@pytest.mark.unit
def test_to_dataframe_empty_buffer():
    """Test to_dataframe with empty buffer."""
    buffer = PredictionBuffer(max_records=10)

    df = buffer.to_dataframe()

    assert df.empty


@pytest.mark.unit
def test_stats_empty_buffer():
    """Test stats with empty buffer."""
    buffer = PredictionBuffer(max_records=10)

    stats = buffer.stats()

    assert stats["total_records"] == 0
    assert stats["by_version"] == {}
    assert stats["latest_timestamp"] is None


@pytest.mark.unit
def test_prediction_record_auto_generates_id():
    """Test that PredictionRecord auto-generates prediction_id."""
    record = PredictionRecord(
        timestamp=datetime.utcnow(),
        model_version="1",
        predicted_emotion="happy",
        confidence=0.9,
        probabilities={"happy": 0.9},
        features={"f": 0.5},
    )

    assert record.prediction_id is not None
    assert len(record.prediction_id) == 36  # UUID format


@pytest.mark.unit
def test_prediction_record_preserves_provided_id():
    """Test that PredictionRecord preserves provided prediction_id."""
    custom_id = "custom-id-12345"
    record = PredictionRecord(
        timestamp=datetime.utcnow(),
        model_version="1",
        predicted_emotion="happy",
        confidence=0.9,
        probabilities={"happy": 0.9},
        features={"f": 0.5},
        prediction_id=custom_id,
    )

    assert record.prediction_id == custom_id


@pytest.mark.unit
def test_prediction_record_to_row():
    """Test PredictionRecord to_row conversion."""
    record = PredictionRecord(
        timestamp=datetime.utcnow(),
        model_version="1",
        predicted_emotion="happy",
        confidence=0.9,
        probabilities={"happy": 0.9, "sad": 0.1},
        features={"feature_a": 0.5, "feature_b": 1.0},
        actual_emotion="happy",
        filename="test.wav",
        api_version="v2",
    )

    row = record.to_row()

    assert row["prediction_id"] == record.prediction_id
    assert row["model_version"] == "1"
    assert row["api_version"] == "v2"
    assert row["predicted_emotion"] == "happy"
    assert row["actual_emotion"] == "happy"
    assert row["confidence"] == 0.9
    assert row["filename"] == "test.wav"
    # Features are included
    assert row["feature_a"] == 0.5
    assert row["feature_b"] == 1.0
    # Probabilities are prefixed
    assert row["proba_happy"] == 0.9
    assert row["proba_sad"] == 0.1


@pytest.mark.unit
def test_buffer_respects_max_records():
    """Test that buffer evicts old records when max is reached."""
    buffer = PredictionBuffer(max_records=2)

    now = datetime.utcnow()
    buffer.add(_record(now, version="1"))
    buffer.add(_record(now + timedelta(seconds=1), version="2"))
    buffer.add(_record(now + timedelta(seconds=2), version="3"))

    stats = buffer.stats()

    # Should only have 2 records (most recent)
    assert stats["total_records"] == 2
    assert "1" not in stats["by_version"]
    assert stats["by_version"] == {"2": 1, "3": 1}


@pytest.mark.unit
def test_stats_tracks_api_versions():
    """Test that stats tracks API versions correctly."""
    buffer = PredictionBuffer(max_records=10)

    now = datetime.utcnow()
    record_v1 = PredictionRecord(
        timestamp=now,
        model_version="1",
        predicted_emotion="happy",
        confidence=0.9,
        probabilities={"happy": 0.9},
        features={"f": 0.5},
        api_version="v1",
    )
    record_v2 = PredictionRecord(
        timestamp=now + timedelta(seconds=1),
        model_version="1",
        predicted_emotion="sad",
        confidence=0.8,
        probabilities={"sad": 0.8},
        features={"f": 0.6},
        api_version="v2",
    )

    buffer.add(record_v1)
    buffer.add(record_v2)

    stats = buffer.stats()

    assert stats["by_api_version"] == {"v1": 1, "v2": 1}
