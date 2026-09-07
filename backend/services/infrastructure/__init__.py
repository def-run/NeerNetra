__all__ = ["ExposureAnalyzer"]


def __getattr__(name):
    if name == "ExposureAnalyzer":
        from backend.services.infrastructure.exposure_analyzer import ExposureAnalyzer

        return ExposureAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
