"""Public prediction service exports."""

__all__ = ["PredictionService"]


def __getattr__(name):
    if name == "PredictionService":
        from backend.services.prediction.prediction_service import PredictionService

        return PredictionService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
