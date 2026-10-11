"""OLS coefficient scores and calendar covariance for matched outcomes."""
import hashlib,subprocess
import numpy as np

def ols(x: np.ndarray, y: np.ndarray):
    if x.ndim != 2 or len(x) != len(y) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Invalid regression dimensions or nonfinite input')
    n, k = x.shape
    if n <= k or np.linalg.matrix_rank(x) != k:
        raise ValueError('Unique coefficients and positive residual degrees of freedom required')
    q, r = np.linalg.qr(x, mode='reduced')
    coefficients = np.linalg.solve(r, q.T @ y)
    residuals = y - x @ coefficients
    inverse_r = np.linalg.solve(r, np.eye(k))
    # Rows are coefficient contributions, not the n-scaled influence functions.
    linear_operator_transpose = q @ inverse_r.T
    return coefficients, residuals, linear_operator_transpose, np.sum(q*q, axis=1)

def calendar_hac(influences: np.ndarray, calendar: np.ndarray, bandwidth: int,
                 correction: float = 1.) -> np.ndarray:
    # The inputs already contain the OLS 1/n scaling; no extra n divisor follows.
    if (influences.ndim != 2 or calendar.ndim != 1
            or len(influences) != len(calendar) or len(calendar) == 0
            or not np.issubdtype(calendar.dtype, np.signedinteger)
            or np.any(np.diff(calendar) <= 0)
            or not isinstance(bandwidth, (int, np.integer)) or bandwidth < 0
            or not np.isfinite(correction) or correction <= 0
            or not np.isfinite(influences).all()):
        raise ValueError('Invalid influence scores or calendar')
    distance = calendar - calendar[0]
    embedded = np.zeros((int(distance[-1])+1, influences.shape[1]))
    embedded[distance] = influences
    covariance = embedded.T @ embedded
    for lag in range(1, min(bandwidth, len(embedded)-1)+1):
        cross = embedded[lag:].T @ embedded[:-lag]
        covariance += (1-lag/(bandwidth+1)) * (cross+cross.T)
    covariance = correction * (covariance + covariance.T) / 2
    if not np.isfinite(covariance).all():
        raise ValueError('Nonfinite HAC covariance')
    tolerance = 1e-9 * max(1., np.max(np.abs(covariance)))
    if np.min(np.linalg.eigvalsh(covariance)) < -tolerance:
        raise ValueError('HAC covariance failed positive-semidefiniteness check')
    return covariance


def compare_values(actual,expected,path='root'):
    if isinstance(actual,dict):
        if set(actual)!=set(expected):raise ValueError(f'Fields differ:{path}')
        return sum(compare_values(actual[k],expected[k],path+'.'+k) for k in actual)
    if isinstance(actual,list):
        if len(actual)!=len(expected):raise ValueError(f'Lengths differ:{path}')
        return sum(compare_values(a,b,path+f'.{i}') for i,(a,b) in enumerate(zip(actual,expected)))
    if isinstance(actual,(float,int)) and not isinstance(actual,bool):
        if not np.isclose(actual,expected,rtol=1e-9,atol=1e-10):raise ValueError(f'Numeric difference:{path}')
        return 1
    if actual!=expected:raise ValueError(f'Value differs:{path}')
    return 0


PRESERVED_REVISION='26327908a873de7e1f6b027645d45582bdb256ac'
def verify_historical_evidence(root,records):
    for name,wanted in records.items():
        path=root/name
        if path.exists():
            content=path.read_bytes()
        else:
            try:
                content=subprocess.check_output(['git','show',PRESERVED_REVISION+':'+name],cwd=root,stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as error:
                raise ValueError('Historical evidence verification requires the complete Git checkout') from error
        if hashlib.sha256(content).hexdigest()!=wanted:
            raise ValueError('Earlier retained evidence changed:'+name)
