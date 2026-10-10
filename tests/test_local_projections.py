"""Algebraic fixtures check domains, calendar dependence and confidence mapping."""
import numpy as np
import pytest
from scipy.stats import norm
from local_projections import calendar_hac, ols, product_interval


def test_calendar_gaps_are_not_compressed():
    # Three abstract score values, not empirical observations.
    scores=np.array([[1.],[2.],[3.]])
    covariance=calendar_hac(scores,np.array([10,12,13]),1)
    # Sum of squares is 14; only the 12/13 pair has distance one.
    assert covariance[0,0] == pytest.approx(14+2*.5*2*3)
    assert covariance[0,0] != pytest.approx(calendar_hac(scores,np.array([10,11,12]),1)[0,0])


def test_cross_equation_covariance_and_common_correction():
    scores=np.array([[1.,2.],[2.,-1.],[0.,3.]])
    expected=np.array([[5.,0.],[0.,14.]])*1.5
    assert np.allclose(calendar_hac(scores,np.array([1,2,3]),0,1.5),expected)
    assert np.allclose(calendar_hac(scores,np.array([1,2,3]),0),scores.T@scores)


def test_zero_gradient_product_is_not_zero_width():
    lo,hi=product_interval(0.,0.,1.,2.)
    critical=norm.ppf(.9875)
    assert lo == pytest.approx(-2*critical**2)
    assert hi == pytest.approx(2*critical**2)
    assert lo < 0 < hi


def test_invalid_regression_and_marginal_domains():
    with pytest.raises(ValueError):
        ols(np.ones((4,2)),np.arange(4.))
    with pytest.raises(ValueError):
        product_interval(1.,2.,0.,1.)
    with pytest.raises(ValueError):
        product_interval(float("nan"),2.,1.,1.)
    with pytest.raises(ValueError):
        product_interval(1e30,2.,1.,1.)
    with pytest.raises(ValueError):
        calendar_hac(np.ones((2,1)),np.array([1,1]),1)
