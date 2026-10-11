"""Deterministic algebra tests; no empirical observations are used."""

from decimal import Decimal, localcontext
import random
import unittest

from ar_inference import ar_inverse_set, quadratic_leq_zero


class QuadraticSets(unittest.TestCase):
    def test_all_topologies(self):
        cases = [
            ((1, -3, 2), "bounded_interval", [(1, 2)]),
            ((-1, 3, -2), "two_rays", [(None, 1), (2, None)]),
            ((0, 2, -4), "left_halfline", [(None, 2)]),
            ((0, -2, 4), "right_halfline", [(2, None)]),
            ((-1, 2, -1), "whole_real_line", [(None, None)]),
            ((0, 0, 0), "whole_real_line", [(None, None)]),
            ((0, 0, -1), "whole_real_line", [(None, None)]),
            ((1, 0, 1), "empty", []),
            ((0, 0, 1), "empty", []),
            ((1, -2, 1), "isolated_point", [(1, 1)]),
        ]
        for args, kind, intervals in cases:
            with self.subTest(args=args):
                result = quadratic_leq_zero(*args)
                self.assertEqual(result.kind, kind)
                self.assertEqual([(i.lower, i.upper) for i in result.intervals],
                                 intervals)

    def test_near_linear_keeps_distant_endpoint(self):
        positive = quadratic_leq_zero("1e-30", 1, -1)
        negative = quadratic_leq_zero("-1e-30", 1, -1)
        self.assertEqual(positive.kind, "bounded_interval")
        self.assertEqual(negative.kind, "two_rays")
        self.assertLess(positive.intervals[0].lower, Decimal("-9e29"))
        self.assertGreater(negative.intervals[1].lower, Decimal("9e29"))
        for value in (-100, 0, Decimal("0.9"), 2, 100):
            self.assertEqual(positive.contains(value), value <= 1)
            self.assertEqual(negative.contains(value), value <= 1)

    def test_near_constant_limits(self):
        self.assertEqual(quadratic_leq_zero("1e-30", 0, -1).kind,
                         "bounded_interval")
        self.assertEqual(quadratic_leq_zero("-1e-30", 0, 1).kind,
                         "two_rays")
        self.assertTrue(quadratic_leq_zero("1e-30", 0, -1).contains(100))
        self.assertFalse(quadratic_leq_zero("-1e-30", 0, 1).contains(100))
        self.assertEqual(quadratic_leq_zero(0, "1e-30", 1).kind,
                         "left_halfline")
        self.assertLess(quadratic_leq_zero(0, "1e-30", 1).intervals[0].upper,
                        Decimal("-9e29"))

    def test_small_root_survives_cancellation(self):
        result = quadratic_leq_zero(1, "1e30", 1)
        root = result.intervals[0].upper
        self.assertLess(root, 0)
        self.assertLess(abs(root + Decimal("1e-30")), Decimal("1e-80"))

    def test_membership_matches_polynomial(self):
        rng = random.Random(483)
        for _ in range(1000):
            a, b, c = (rng.randint(-20, 20) for _ in range(3))
            result = quadratic_leq_zero(a, b, c)
            for denominator in (1, 4, 10):
                for numerator in range(-40, 41):
                    value = Decimal(numerator) / denominator
                    value_polynomial = a * value * value + b * value + c
                    self.assertEqual(result.contains(value), value_polynomial <= 0)


class ARSets(unittest.TestCase):
    def test_ar_topologies(self):
        cases = [
            ((2, 1, ".25", ".01", 0), "bounded_interval"),
            ((1, ".1", ".01", 1, 0), "two_rays"),
            ((2, 1, 1, 1, 0), "right_halfline"),
            ((-2, 1, 1, 1, 0), "left_halfline"),
            ((0, 0, 1, 1, 0), "whole_real_line"),
            ((1, 0, 0, 0, 0), "empty"),
            ((2, 1, 1, ".25", ".5"), "isolated_point"),
        ]
        for args, kind in cases:
            with self.subTest(args=args):
                self.assertEqual(ar_inverse_set(*args, critical_square=1).kind,
                                 kind)

    def test_nonzero_first_stage_ratio_is_accepted(self):
        rng = random.Random(77)
        with localcontext() as context:
            context.prec = 80
            for _ in range(1000):
                # Integer Cholesky entries yield exactly PSD covariance.
                l11, l21, l22 = (Decimal(rng.randint(1, 8)),
                                Decimal(rng.randint(-8, 8)),
                                Decimal(rng.randint(1, 8)))
                vr, vf, cov = l11 ** 2, l21 ** 2 + l22 ** 2, l11 * l21
                r = Decimal(rng.randint(-20, 20))
                f = Decimal(rng.choice([i for i in range(-20, 21) if i]))
                result = ar_inverse_set(r, f, vr, vf, cov, critical_square=1)
                self.assertNotEqual(result.kind, "empty")
                self.assertNotEqual(result.kind, "isolated_point")
                self.assertTrue(result.contains(r / f))

    def test_ten_basis_point_reporting_scale(self):
        one = ar_inverse_set(2, 1, ".25", ".01", 0, critical_square=1)
        ten = ar_inverse_set(2, 1, ".25", ".01", 0, critical_square=1,
                             effect_size=10)
        self.assertEqual(one.kind, ten.kind)
        with localcontext() as context:
            context.prec = 100
            self.assertEqual(ten.intervals[0].lower,
                             10 * one.intervals[0].lower)
            self.assertEqual(ten.intervals[0].upper,
                             10 * one.intervals[0].upper)

    def test_negative_covariance_determinant_is_rejected(self):
        with self.assertRaises(ValueError):
            ar_inverse_set(2, 1, 1, 1, "1.01")


if __name__ == "__main__":
    unittest.main()
