"""Pure-Python classification of a scalar HAC Anderson--Rubin inverse set.

This file contains algebra only: no data acquisition or regressions.
Decimal arithmetic preserves the topology at small but nonzero coefficients.
No coefficient is silently rounded to zero.  Endpoints are closed; None
denotes the corresponding infinite endpoint.
"""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from statistics import NormalDist
from typing import Optional, Union


Number = Union[int, float, str, Decimal]


def _decimal(value: Number) -> Decimal:
    value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not value.is_finite():
        raise ValueError("All coefficients must be finite.")
    return value


@dataclass(frozen=True)
class Interval:
    lower: Optional[Decimal]
    upper: Optional[Decimal]

    def contains(self, value: Number) -> bool:
        value = _decimal(value)
        return ((self.lower is None or self.lower <= value)
                and (self.upper is None or value <= self.upper))


@dataclass(frozen=True)
class InverseSet:
    kind: str
    intervals: tuple[Interval, ...]
    coefficients: tuple[Decimal, Decimal, Decimal]
    discriminant: Optional[Decimal]
    notes: tuple[str, ...] = ()

    def contains(self, value: Number) -> bool:
        return any(interval.contains(value) for interval in self.intervals)

    def scaled(self, positive_scale: Number) -> "InverseSet":
        scale = _decimal(positive_scale)
        if scale <= 0:
            raise ValueError("The reporting scale must be positive.")
        a, b, c = self.coefficients
        with localcontext() as context:
            context.prec = 100
            intervals = tuple(Interval(None if i.lower is None else i.lower * scale,
                                       None if i.upper is None else i.upper * scale)
                              for i in self.intervals)
            # New argument theta = scale * beta, so beta = theta / scale.
            coefficients = (a / scale ** 2, b / scale, c)
            discriminant = (None if self.discriminant is None
                            else self.discriminant / scale ** 2)
        return InverseSet(self.kind, intervals, coefficients, discriminant,
                          self.notes)

    def as_dict(self) -> dict:
        """String endpoints preserve arbitrarily large, finite Decimal roots."""
        return {
            "kind": self.kind,
            "intervals": [{"lower": None if i.lower is None else str(i.lower),
                           "upper": None if i.upper is None else str(i.upper)}
                          for i in self.intervals],
            "coefficients": [str(x) for x in self.coefficients],
            "discriminant": (None if self.discriminant is None
                             else str(self.discriminant)),
            "notes": list(self.notes),
        }


def quadratic_leq_zero(a: Number, b: Number, c: Number) -> InverseSet:
    """Exactly classify a beta**2 + b beta + c <= 0.

    Inputs are interpreted as their displayed decimal values.  For example,
    A=1e-30 remains quadratic: its distant endpoint is retained rather than
    replacing the set by the limiting halfline.  Constant and linear cases
    require exactly zero coefficients.  The implementation uses a stable
    q-formula for roots and obtains the second root from their product.
    """
    a, b, c = map(_decimal, (a, b, c))
    with localcontext() as context:
        context.prec = max(100, 4 * max(len(v.as_tuple().digits)
                                       for v in (a, b, c)))
        coefficients = (a, b, c)
        if a == 0:
            if b == 0:
                if c <= 0:
                    return InverseSet("whole_real_line", (Interval(None, None),),
                                      coefficients, None)
                return InverseSet("empty", (), coefficients, None)
            endpoint = -c / b
            if b > 0:
                return InverseSet("left_halfline", (Interval(None, endpoint),),
                                  coefficients, None)
            return InverseSet("right_halfline", (Interval(endpoint, None),),
                              coefficients, None)

        discriminant = b * b - 4 * a * c
        if discriminant < 0:
            if a < 0:
                return InverseSet("whole_real_line", (Interval(None, None),),
                                  coefficients, discriminant)
            return InverseSet("empty", (), coefficients, discriminant)
        if discriminant == 0:
            if a < 0:
                return InverseSet("whole_real_line", (Interval(None, None),),
                                  coefficients, discriminant)
            root = -b / (2 * a)
            return InverseSet("isolated_point", (Interval(root, root),),
                              coefficients, discriminant)

        root_discriminant = discriminant.sqrt()
        signed_root = root_discriminant if b >= 0 else -root_discriminant
        q = -(b + signed_root) / 2
        roots = sorted((q / a, c / q))
        if a > 0:
            return InverseSet("bounded_interval", (Interval(*roots),),
                              coefficients, discriminant)
        return InverseSet("two_rays", (Interval(None, roots[0]),
                                        Interval(roots[1], None)),
                          coefficients, discriminant)


def ar_inverse_set(reduced_form: Number, first_stage: Number,
                   variance_reduced_form: Number,
                   variance_first_stage: Number,
                   covariance: Number, *,
                   critical_square: Number = NormalDist().inv_cdf(.975) ** 2,
                   effect_size: Number = 1) -> InverseSet:
    """Invert a scalar AR score test using one common HAC coefficient matrix.

    RF and FS regressions must use identical rows, controls, instrument,
    calendar bandwidth and finite-sample multiplier.  The tested moment is
    RF - beta * FS.  Set effect_size=10 for an output response per ten basis
    points when the financial indicator is in basis points.

    The covariance is required to be PSD.  This algebraic routine does not
    repair a negative eigenvalue or infer a positive-definite score limit.
    Singular matrices receive an explicit coverage-regularity note.  At zero
    estimated null-score variance the polynomial convention accepts 0 <= 0;
    a chi-square test is not itself justified by a 0/0 statistic.
    """
    r, f, vr, vf, cov, critical, effect_size = map(
        _decimal, (reduced_form, first_stage, variance_reduced_form,
                   variance_first_stage, covariance, critical_square,
                   effect_size))
    if critical <= 0 or effect_size <= 0:
        raise ValueError("Critical square and effect size must be positive.")
    if vr < 0 or vf < 0:
        raise ValueError("Negative marginal variance.")
    with localcontext() as context:
        context.prec = max(100, 4 * max(len(v.as_tuple().digits)
                                       for v in (r, f, vr, vf, cov, critical)))
        determinant = vr * vf - cov * cov
        if determinant < 0:
            raise ValueError("Joint covariance is not positive semidefinite.")
        a = f * f - critical * vf
        b = -2 * r * f + 2 * critical * cov
        c = r * r - critical * vr
        result = quadratic_leq_zero(a, b, c).scaled(effect_size)
        notes = []
        if determinant == 0:
            notes.append("Singular covariance: check nondegenerate null-score "
                         "inference before assigning nominal coverage.")
        if result.kind == "empty":
            # For PSD covariance an empty set requires f=vf=0.
            if not (f == 0 and vf == 0):
                raise AssertionError("Empty AR set contradicts PSD covariance.")
            notes.append("The fitted financial normaliser and its variance "
                         "are both zero; every finite ratio is rejected.")
        return InverseSet(result.kind, result.intervals, result.coefficients,
                          result.discriminant, tuple(notes))
