__all__ = ["ArrivalTimeEstimator"]


def __getattr__(name):
    if name == "ArrivalTimeEstimator":
        from backend.services.arrival_time.arrival_estimator import ArrivalTimeEstimator

        return ArrivalTimeEstimator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
