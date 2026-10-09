"""Three-grid scalar solution convergence assessment, separate from solver residual convergence."""

import math


def three_grid_convergence(mesh_sizes, values, *, maximum_relative_gci=0.05, safety_factor=1.25):
    h = tuple(float(x) for x in mesh_sizes)
    phi = tuple(float(x) for x in values)
    if len(h) != 3 or len(phi) != 3 or not all(math.isfinite(x) for x in (*h, *phi)):
        raise ValueError("Three finite coarse-to-fine mesh sizes and endpoint values are required")
    if (
        not h[0] > h[1] > h[2] > 0
        or not math.isfinite(maximum_relative_gci)
        or maximum_relative_gci < 0
    ):
        raise ValueError(
            "Mesh sizes must strictly decrease and GCI tolerance must be nonnegative finite"
        )
    if not math.isfinite(safety_factor) or safety_factor < 1:
        raise ValueError("Safety factor must be finite and >=1")
    r = h[0] / h[1]
    if not math.isclose(r, h[1] / h[2], rel_tol=1e-6):
        raise ValueError("This GCI assessment requires a constant refinement ratio")
    d1 = phi[0] - phi[1]
    d2 = phi[1] - phi[2]
    if d1 * d2 <= 0 or abs(d1) <= abs(d2) or phi[2] == 0:
        return {
            "passed": False,
            "status": "asymptotic_convergence_not_demonstrated",
            "reason": (
                "Oscillatory, exact/degenerate or non-decreasing differences; "
                "zero reference endpoint"
            ),
        }
    order = math.log(abs(d1 / d2)) / math.log(r)
    denominator = r**order - 1
    absolute = safety_factor * abs(d2) / denominator
    relative = absolute / abs(phi[2])
    return {
        "passed": relative <= maximum_relative_gci,
        "status": "assessed",
        "observed_order": order,
        "fine_grid_relative_gci": relative,
        "fine_grid_absolute_gci": absolute,
        "extrapolated_endpoint": phi[2] + (phi[2] - phi[1]) / denominator,
        "refinement_ratio": r,
        "safety_factor": safety_factor,
        "scope": "scalar endpoint, monotone asymptotic three-grid model; not empirical validation",
    }
