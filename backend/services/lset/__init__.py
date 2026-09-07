__all__ = ["LSETCalculator"]


def __getattr__(name):
    if name == "LSETCalculator":
        from backend.services.lset.lset_calculator import LSETCalculator

        return LSETCalculator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
