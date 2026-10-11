"""Analytic global-optimum checks for confidence-set projection."""
import numpy as np
from joint_stability import quadratic_ball_minimum

def test_compatible_singular_boundary():
    result=quadratic_ball_minimum(np.diag([-2.,1.]),np.zeros(2),0.)
    assert np.isclose(result['value'],-2.)
    assert np.isclose(np.linalg.norm(result['point_on_unit_ball']),1.)
    assert result['shifted_hessian_smallest_eigenvalue']>=-1e-12

def test_positive_definite_interior():
    result=quadratic_ball_minimum(np.diag([1.,2.]),np.array([-1.,0.]),0.)
    assert np.isclose(result['value'],-.25)
    assert np.allclose(result['point_on_unit_ball'],[.5,0.])
    assert result['multiplier']==0.

def test_constant_objective():
    result=quadratic_ball_minimum(np.zeros((2,2)),np.zeros(2),3.)
    assert result['value']==3.
    assert result['multiplier']==0.
