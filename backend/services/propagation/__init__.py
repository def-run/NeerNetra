__all__ = ["FloodPropagationEngine"]


def __getattr__(name):
    if name == "FloodPropagationEngine":
        from backend.services.propagation.flood_propagation import FloodPropagationEngine

        return FloodPropagationEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
