"""Checks for repeated event months and generated current-purge invariance."""
import numpy as np
from local_projections import ols
from us_purchases import clustered_hac

def test_same_month_scores_use_all_calendar_pairs():
    # Two decisions in one month must retain their cross product; a skipped month
    # must retain its true distance rather than compressing the calendar.
    dates=np.array([10,10,12,15],dtype=np.int64)
    scores=np.array([[1.,2.],[-.5,1.],[2.,-1.],[3.,.5]])
    L=3
    distances=abs(dates[:,None]-dates[None,:])
    weights=np.maximum(0.,1-distances/(L+1))
    expected=1.2*scores.T@weights@scores
    np.testing.assert_allclose(clustered_hac(scores,dates,L,1.2),expected,rtol=1e-13,atol=1e-13)

def test_purge_perturbations_cancel_only_with_complete_conditioning_span():
    rng=np.random.default_rng(919)
    f=np.column_stack([np.ones(40),rng.normal(size=(40,3))])
    t=rng.normal(size=40);y=rng.normal(size=(40,2))
    z1=t-f@np.array([.5,1.,-.3,.2]);z2=t-f@np.array([-.7,.1,1.3,-.2])
    a=ols(np.column_stack([z1,f]),y);b=ols(np.column_stack([z2,f]),y)
    for x,z in [(a[0][0],b[0][0]),(a[1],b[1]),(a[2][:,0],b[2][:,0]),(a[3],b[3])]:
        np.testing.assert_allclose(x,z,rtol=1e-12,atol=1e-12)
    # Deliberately omit one source predictor: cancellation should no longer hold.
    omitted_a=ols(np.column_stack([z1,f[:,:-1]]),y)[0][0]
    omitted_b=ols(np.column_stack([z2,f[:,:-1]]),y)[0][0]
    assert np.max(abs(omitted_a-omitted_b))>1e-4
