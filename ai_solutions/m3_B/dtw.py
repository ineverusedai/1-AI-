import numpy as np

INF = 1e18


def dtw_cost(C):
    """DTW with steps (1,1),(1,2),(2,1); slope constraint 1/2..2. Rows vectorized.
    Returns normalized cost (by n+m). Ends are open-free: full path from (0,0) to (n-1,m-1)."""
    n, m = C.shape
    D = np.full((n + 2, m + 2), INF)
    D[1, 1] = 0.0  # virtual start; real cell (i,j) stored at (i+2, j+2)
    D = np.full((n + 2, m + 2), INF)
    D[2, 2] = C[0, 0]
    for i in range(1, n):
        a = D[i + 1, 1:m + 1]       # (i-1, j-1)
        b = D[i + 1, 0:m]           # (i-1, j-2)
        c = D[i, 1:m + 1]           # (i-2, j-1)
        best = np.minimum(np.minimum(a, b), c)
        D[i + 2, 2:] = C[i] + best
    return D[n + 1, m + 1] / (n + m)


def dtw_path(C):
    """Same recursion as dtw_cost, returns (cost, ii, jj) of the optimal path."""
    n, m = C.shape
    D = np.full((n + 2, m + 2), INF)
    B = np.zeros((n, m), np.int8)
    D[2, 2] = C[0, 0]
    for i in range(1, n):
        a = D[i + 1, 1:m + 1]; b = D[i + 1, 0:m]; c = D[i, 1:m + 1]
        st = np.stack([a, b, c]); k = st.argmin(0)
        D[i + 2, 2:] = C[i] + st[k, np.arange(m)]
        B[i] = k
    cost = D[n + 1, m + 1]
    ii, jj = [n - 1], [m - 1]
    i, j = n - 1, m - 1
    if cost >= INF / 2:
        return cost / (n + m), None, None
    while i > 0 or j > 0:
        k = B[i, j]
        if k == 0: i, j = i - 1, j - 1
        elif k == 1: i, j = i - 1, j - 2
        else: i, j = i - 2, j - 1
        ii.append(i); jj.append(j)
    return cost / (n + m), np.array(ii[::-1]), np.array(jj[::-1])
