__all__ = ["CascadeAnalyzer"]


def __getattr__(name):
    if name == "CascadeAnalyzer":
        from backend.services.cascade.cascade_analyzer import CascadeAnalyzer

        return CascadeAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
