"""
NeerNetra — Flood Propagation Service
=======================================
Simplified spatial flood propagation over terrain grid.
Phase 4 implementation.
"""


class PropagationService:
    """Service for estimating flood propagation across spatial grid."""

    def propagate(self, origin_lat: float, origin_lon: float, time_steps: int) -> dict:
        """
        Estimate flood propagation from a high-risk origin point.

        Uses simplified raster/grid and terrain connectivity.
        Not a full hydrodynamic solver.
        """
        raise NotImplementedError("Phase 4: Flood Dynamics")
