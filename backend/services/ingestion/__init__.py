__all__ = ["IngestionPipeline"]


def __getattr__(name):
    if name == "IngestionPipeline":
        from backend.services.ingestion.pipeline import IngestionPipeline

        return IngestionPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
