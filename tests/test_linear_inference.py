"""Checks for calendar gaps, joint scores and rank requirements."""
import numpy as np
import pytest
from linear_inference import calendar_hac,ols

def test_calendar_gaps_are_not_compressed():
    scores=np.array([[1.],[2.],[3.]])
    covariance=calendar_hac(scores,np.array([10,12,13]),1)
    assert covariance[0,0]==pytest.approx(14+2*.5*2*3)
    assert covariance[0,0]!=pytest.approx(calendar_hac(scores,np.array([10,11,12]),1)[0,0])

def test_cross_equation_covariance_and_common_correction():
    scores=np.array([[1.,2.],[2.,-1.],[0.,3.]])
    expected=np.array([[5.,0.],[0.,14.]])*1.5
    np.testing.assert_allclose(calendar_hac(scores,np.array([1,2,3]),0,1.5),expected)
    np.testing.assert_allclose(calendar_hac(scores,np.array([1,2,3]),0),scores.T@scores)

def test_invalid_rank_and_duplicate_calendar_rejected():
    with pytest.raises(ValueError):ols(np.ones((4,2)),np.arange(4.))
    with pytest.raises(ValueError):calendar_hac(np.ones((2,1)),np.array([1,1]),1)
