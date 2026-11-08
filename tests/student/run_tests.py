"""
My own tests for Assignment 4 (Java solution).

Run from the repository root:
    python tests/student/run_tests.py

The script compiles Java/source, starts ONE java process per group of requests
(like the official JSONL batches) and compares the answers with small oracles
that I wrote separately in Python (brute force / memoised recursion / sorting
of real suffix strings). The oracles do not use the DP or automaton ideas of
the Java code on purpose, so a shared bug is unlikely.
"""
import itertools
import json
import pathlib
import random
import subprocess
import sys
import time
from functools import lru_cache

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / 'Java' / 'source'
BUILD = ROOT / 'Java' / 'build'

random.seed(4242)
failures = 0
total = 0


# ------------------------------------------------------------------
# running java
# ------------------------------------------------------------------
def compile_java():
    BUILD.mkdir(exist_ok=True)
    files = sorted(str(p) for p in SRC.glob('*.java'))
    subprocess.run(['javac', '--release', '17', '-encoding', 'UTF-8', '-d', str(BUILD), *files],
                   check=True, stderr=subprocess.DEVNULL, timeout=60)


def run_batch(requests, timeout=20):
    data = ''.join(json.dumps(r, separators=(',', ':')) + '\n' for r in requests)
    t0 = time.time()
    p = subprocess.run(['java', '-Xmx384m', '-cp', str(BUILD), 'Main'], input=data,
                       capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    dt = time.time() - t0
    if p.returncode != 0:
        raise RuntimeError('java exited with %d: %s' % (p.returncode, p.stderr[-500:]))
    lines = p.stdout.splitlines()
    if len(lines) != len(requests):
        raise RuntimeError('expected %d lines, got %d' % (len(requests), len(lines)))
    return [json.loads(l) for l in lines], dt


# ------------------------------------------------------------------
# oracles (independent of the Java code)
# ------------------------------------------------------------------
def is_subseq(s, t):
    it = iter(t)
    return all(c in it for c in s)


def oracle_lcs_len(a, b):
    @lru_cache(maxsize=None)
    def f(i, j):
        if i == len(a) or j == len(b):
            return 0
        if a[i] == b[j]:
            return 1 + f(i + 1, j + 1)
        return max(f(i + 1, j), f(i, j + 1))
    return f(0, 0)


def oracle_merge_cost(sizes):
    """try every possible adjacent merge order (exponential, only for n<=7)"""
    @lru_cache(maxsize=None)
    def f(blocks):
        if len(blocks) <= 1:
            return 0
        best = None
        for i in range(len(blocks) - 1):
            s = blocks[i] + blocks[i + 1]
            c = s + f(blocks[:i] + (s,) + blocks[i + 2:])
            if best is None or c < best:
                best = c
        return best
    return f(tuple(sizes))


def check_merge_plan(sizes, plan, cost):
    blocks = [(i, i) for i in range(len(sizes))]
    total = 0
    for l, k, r in plan:
        if (l, k) not in blocks:
            return False
        j = blocks.index((l, k))
        if j + 1 >= len(blocks) or blocks[j + 1] != (k + 1, r):
            return False
        blocks[j:j + 2] = [(l, r)]
        total += sum(sizes[l:r + 1])
    return len(plan) == max(0, len(sizes) - 1) and len(blocks) <= 1 and total == cost


def oracle_tree_brute(n, w, edges):
    best = 0
    for mask in range(1 << n):
        if any((mask >> u) & 1 and (mask >> v) & 1 for u, v in edges):
            continue
        s = sum(w[i] for i in range(n) if (mask >> i) & 1)
        best = max(best, s)
    return best


def check_tree(req, resp, expected_weight):
    sel = resp['selected']
    chosen = set(sel)
    return (len(chosen) == len(sel) and all(0 <= v < req['n'] for v in sel)
            and not any(u in chosen and v in chosen for u, v in req['edges'])
            and sum(req['weights'][v] for v in sel) == resp['weight'] == expected_weight)


def tree_dp_python(n, w, edges):
    """second, separately written linear DP (parent array via stack) for big trees"""
    if n == 0:
        return 0
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    # use root n-1 so it differs from the Java root (0)
    root = n - 1
    par = [-2] * n
    par[root] = -1
    stack = [root]
    order = []
    while stack:
        v = stack.pop()
        order.append(v)
        for u in adj[v]:
            if par[u] == -2:
                par[u] = v
                stack.append(u)
    inc = list(w)
    exc = [0] * n
    for v in reversed(order):
        p = par[v]
        if p >= 0:
            inc[p] += exc[v]
            exc[p] += max(inc[v], exc[v])
    return max(inc[root], exc[root])


def positions_oracle(text, pat):
    n, m = len(text), len(pat)
    if m == 0:
        return list(range(n + 1))
    return [i for i in range(n - m + 1) if text[i:i + m] == pat]


def positions_fast(text, pat):
    """for the large tests: python's own find in a loop (only used in tests)"""
    n, m = len(text), len(pat)
    if m == 0:
        return list(range(n + 1))
    res = []
    i = text.find(pat)
    while i != -1:
        res.append(i)
        i = text.find(pat, i + 1)
    return res


def suffix_oracle(text):
    n = len(text)
    sa = sorted(range(n), key=lambda i: text[i:])
    lcp = [0] * n
    for i in range(1, n):
        a, b = text[sa[i - 1]:], text[sa[i]:]
        k = 0
        while k < len(a) and k < len(b) and a[k] == b[k]:
            k += 1
        lcp[i] = k
    return sa, lcp


def occurrences(text, s):
    return sum(text.startswith(s, i) for i in range(len(text)))


def aho_oracle(patterns, texts):
    return [[len(positions_oracle(t, p)) for p in patterns] for t in texts]


def rand_str(n, alphabet):
    return ''.join(random.choice(alphabet) for _ in range(n))


# ------------------------------------------------------------------
# test groups. each group = (name, [(request, checker)]), checker(resp) -> bool
# ------------------------------------------------------------------
def eq(expected):
    return lambda resp: resp == expected


def lcs_group():
    cases = []
    # hand-written edge cases with known lengths
    hand = [('', '', 0), ('abc', '', 0), ('', 'abc', 0), ('abc', 'abc', 3), ('abc', 'def', 0),
            ('tea_time', 'team', 4), ('AbC', 'abc', 1), ('a b c', 'abc ', 3),
            ('aaaa', 'aa', 2), ('abcbdab', 'bdcaba', 4), ('xyz', 'zyx', 1), ('!!??', '?!?!', 2)]
    for a, b, L in hand:
        req = {'task': 'lcs', 'a': a, 'b': b}
        cases.append((req, (lambda a, b, L: lambda r: r['length'] == L == len(r['sequence'])
                            and is_subseq(r['sequence'], a) and is_subseq(r['sequence'], b))(a, b, L)))
    for _ in range(300):
        a, b = rand_str(random.randint(0, 9), 'abc'), rand_str(random.randint(0, 9), 'abc')
        L = oracle_lcs_len(a, b)
        req = {'task': 'lcs', 'a': a, 'b': b}
        cases.append((req, (lambda a, b, L: lambda r: r['length'] == L == len(r['sequence'])
                            and is_subseq(r['sequence'], a) and is_subseq(r['sequence'], b))(a, b, L)))
    return cases


def merge_group():
    cases = []
    hand = [[], [5], [2, 3, 4], [0, 0, 0], [1, 1, 1, 1], [10 ** 9] * 7, [4, 1, 1, 4], [3, 0, 3]]
    for s in hand:
        L = oracle_merge_cost(s)
        cases.append(({'task': 'merge', 'sizes': s},
                      (lambda s, L: lambda r: r['cost'] == L and check_merge_plan(s, r['plan'], L))(s, L)))
    for _ in range(200):
        s = [random.choice([0, 1, 2, 5, 9, 10 ** 9]) if random.random() < 0.3 else random.randint(0, 20)
             for _ in range(random.randint(0, 7))]
        L = oracle_merge_cost(s)
        cases.append(({'task': 'merge', 'sizes': s},
                      (lambda s, L: lambda r: r['cost'] == L and check_merge_plan(s, r['plan'], L))(s, L)))
    return cases


def random_tree(n, shape):
    edges = []
    for v in range(1, n):
        if shape == 'chain':
            u = v - 1
        elif shape == 'star':
            u = 0
        else:
            u = random.randint(0, v - 1)
        edges.append([u, v] if random.random() < 0.5 else [v, u])
    random.shuffle(edges)
    return edges


def tree_group():
    cases = []
    hand = [(0, [], []), (1, [5], []), (1, [-5], []), (3, [4, 9, 6], [[0, 1], [1, 2]]),
            (3, [-1, -2, -3], [[0, 1], [1, 2]]), (2, [0, 0], [[0, 1]]), (2, [7, 7], [[0, 1]]),
            (4, [1, 100, 100, 1], [[0, 1], [1, 2], [2, 3]]),
            (3, [10 ** 9, -5, 10 ** 9], [[0, 1], [1, 2]])]
    for n, w, e in hand:
        req = {'task': 'tree', 'n': n, 'weights': w, 'edges': e}
        W = oracle_tree_brute(n, w, e)
        cases.append((req, (lambda req, W: lambda r: check_tree(req, r, W))(req, W)))
    for _ in range(250):
        n = random.randint(1, 12)
        shape = random.choice(['chain', 'star', 'random'])
        w = [random.randint(-10, 10) for _ in range(n)]
        e = random_tree(n, shape)
        req = {'task': 'tree', 'n': n, 'weights': w, 'edges': e}
        W = oracle_tree_brute(n, w, e)
        cases.append((req, (lambda req, W: lambda r: check_tree(req, r, W))(req, W)))
    return cases


def search_group(task):
    cases = []
    hand = [('', ''), ('abc', ''), ('', 'a'), ('abc', 'abcd'), ('aaaaa', 'aaa'), ('abababa', 'aba'),
            ('Hello, World! hello', 'hello'), ('a b  c', ' '), ('a b  c', '  '), ('abdj', 'ab'),
            ('abdj', 'dj'), ('abc', 'abc'), ('mississippi', 'issi'), ('x.y.z', '.'), ('ab', 'b')]
    for t, p in hand:
        cases.append(({'task': task, 'text': t, 'pattern': p}, eq({'positions': positions_oracle(t, p)})))
    for _ in range(300):
        alpha = random.choice(['ab', 'abc', 'a', 'abcdefghij'])
        t, p = rand_str(random.randint(0, 25), alpha), rand_str(random.randint(0, 5), alpha)
        cases.append(({'task': task, 'text': t, 'pattern': p}, eq({'positions': positions_oracle(t, p)})))
    return cases


def rk_extra():
    """pairs with equal hash (base 31, mod 101) but different text: false candidates must be rejected"""
    def h(s):
        v = 0
        for ch in s:
            v = (v * 31 + ord(ch)) % 101
        return v
    cases = []
    # collect colliding pairs of length 2 and 3 by brute force
    pairs = []
    chars = [chr(c) for c in range(32, 127)]
    seen = {}
    for a in chars:
        for b in chars:
            s = a + b
            seen.setdefault(h(s), []).append(s)
    for hv, lst in seen.items():
        if len(lst) >= 2:
            pairs.append((lst[0], lst[1]))
    random.shuffle(pairs)
    assert h('ab') == h('dj') == 75
    for p, q in pairs[:80]:
        t = q + p + q + 'x' + p
        cases.append(({'task': 'rk', 'text': t, 'pattern': p}, eq({'positions': positions_oracle(t, p)})))
    # many collisions in a row: text made only of the colliding twin
    t = 'dj' * 50 + 'ab'
    cases.append(({'task': 'rk', 'text': t, 'pattern': 'ab'}, eq({'positions': [100]})))
    # negative remainder: the outgoing term can be bigger than the whole hash
    for _ in range(300):
        t = rand_str(random.randint(5, 40), chars)
        i = random.randint(0, len(t) - 3)
        p = t[i:i + random.randint(1, 4)]
        cases.append(({'task': 'rk', 'text': t, 'pattern': p}, eq({'positions': positions_oracle(t, p)})))
    return cases


def suffix_check(text):
    sa, lcp = suffix_oracle(text)
    L = max(lcp) if lcp else 0

    def chk(r):
        s = r['repeated']
        return (r['sa'] == sa and r['lcp'] == lcp and len(s) == L
                and (L == 0 or occurrences(text, s) >= 2))
    return chk


def suffix_group():
    cases = []
    hand = ['', 'a', 'aaaa', 'abcd', 'banana', 'abab', 'mississippi', 'aAaA', 'a a a', 'zyxw', 'abcabcabc',
            'xabcyabcz', 'aaaaaaaaaab']
    for t in hand:
        cases.append(({'task': 'suffix', 'text': t}, suffix_check(t)))
    for _ in range(300):
        t = rand_str(random.randint(0, 30), random.choice(['ab', 'abc', 'a', 'abcdefgh']))
        cases.append(({'task': 'suffix', 'text': t}, suffix_check(t)))
    return cases


def aho_group():
    cases = []
    hand = [([], []), ([], ['abc', '']), (['a'], []), (['a'], ['']), (['he', 'she', 'he'], ['sheshe', 'sheshe', '']),
            (['he', 'she', 'his', 'hers'], ['ushers']), (['a', 'aa', 'aaa'], ['aaaa']), (['abc'], ['ab', 'abcabc']),
            (['A', 'a'], ['aAaA']), ([' ', '  '], ['a  b ']), (['x', 'x', 'x'], ['xxx', 'y'])]
    for pats, txts in hand:
        cases.append(({'task': 'aho', 'patterns': pats, 'texts': txts}, eq({'counts': aho_oracle(pats, txts)})))
    for _ in range(300):
        alpha = random.choice(['ab', 'abc', 'a'])
        pats = [rand_str(random.randint(1, 4), alpha) for _ in range(random.randint(0, 6))]
        txts = [rand_str(random.randint(0, 15), alpha) for _ in range(random.randint(0, 4))]
        cases.append(({'task': 'aho', 'patterns': pats, 'texts': txts},
                      eq({'counts': aho_oracle(pats, txts)})))
    return cases


# ------------------------------------------------------------------
# large inputs (the "scale" part): correctness AND time
# ------------------------------------------------------------------
def lcs_big():
    a, b = rand_str(1000, 'abcd'), rand_str(1000, 'abcd')
    prev = [0] * 1001
    for i in range(1, 1001):
        cur = [0] * 1001
        for j in range(1, 1001):
            cur[j] = prev[j - 1] + 1 if a[i - 1] == b[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    L = prev[1000]
    return [({'task': 'lcs', 'a': a, 'b': b},
             lambda r: r['length'] == L == len(r['sequence']) and is_subseq(r['sequence'], a)
             and is_subseq(r['sequence'], b)),
            ({'task': 'lcs', 'a': 'a' * 1000, 'b': 'a' * 1000},
             lambda r: r['length'] == 1000 and r['sequence'] == 'a' * 1000)]


def merge_big():
    out = []
    for sizes in ([10 ** 9] * 200, [random.randint(0, 10 ** 9) for _ in range(200)],
                  [random.randint(0, 3) for _ in range(200)]):
        n = len(sizes)
        pre = [0]
        for x in sizes:
            pre.append(pre[-1] + x)
        dp = [[0] * n for _ in range(n)]
        for ln in range(2, n + 1):
            for l in range(n - ln + 1):
                r = l + ln - 1
                dp[l][r] = min(dp[l][k] + dp[k + 1][r] for k in range(l, r)) + pre[r + 1] - pre[l]
        L = dp[0][n - 1]
        out.append(({'task': 'merge', 'sizes': sizes},
                    (lambda s, L: lambda r: r['cost'] == L and check_merge_plan(s, r['plan'], L))(sizes, L)))
    return out


def tree_big():
    out = []
    n = 100000
    for shape in ('chain', 'star', 'random'):
        w = [random.randint(-10 ** 9, 10 ** 9) for _ in range(n)]
        e = random_tree(n, shape)
        req = {'task': 'tree', 'n': n, 'weights': w, 'edges': e}
        W = tree_dp_python(n, w, e)
        out.append((req, (lambda req, W: lambda r: check_tree(req, r, W))(req, W)))
    # all weights at the maximum on a star with many leaves: the sum is far above 2^31
    w = [10 ** 9] * n
    e = random_tree(n, 'star')
    req = {'task': 'tree', 'n': n, 'weights': w, 'edges': e}
    out.append((req, (lambda req: lambda r: check_tree(req, r, (n - 1) * 10 ** 9))(req)))
    return out


def search_big():
    out = []
    t = 'a' * 200000
    out.append(({'task': 'kmp', 'text': t, 'pattern': 'a' * 100000}, eq({'positions': list(range(100001))})))
    out.append(({'task': 'kmp', 'text': t, 'pattern': 'a' * 99999 + 'b'}, eq({'positions': []})))
    t2 = rand_str(200000, 'ab')
    p2 = rand_str(12, 'ab')
    out.append(({'task': 'kmp', 'text': t2, 'pattern': p2}, eq({'positions': positions_fast(t2, p2)})))
    t3 = 'ab' * 100000
    out.append(({'task': 'kmp', 'text': t3, 'pattern': ''}, eq({'positions': list(range(200001))})))
    # rk at its limit: n*m = 20 000 000
    t4 = 'a' * 10000
    out.append(({'task': 'rk', 'text': t4, 'pattern': 'a' * 2000}, eq({'positions': positions_fast(t4, 'a' * 2000)})))
    out.append(({'task': 'rk', 'text': t4, 'pattern': 'a' * 1999 + 'b'}, eq({'positions': []})))
    t5 = rand_str(10000, 'abcdefghijklmnopqrstuvwxyz ')
    p5 = t5[4000:4020]
    out.append(({'task': 'rk', 'text': t5, 'pattern': p5}, eq({'positions': positions_fast(t5, p5)})))
    # naive at the limit 3000 x 3000
    t6 = 'a' * 3000
    out.append(({'task': 'naive', 'text': t6, 'pattern': 'a' * 1500}, eq({'positions': list(range(1501))})))
    out.append(({'task': 'naive', 'text': t6, 'pattern': 'a' * 2999 + 'b'}, eq({'positions': []})))
    return out


def suffix_big():
    out = []
    n = 50000

    def check(text):
        def chk(r):
            sa, lcp = r['sa'], r['lcp']
            if sorted(sa) != list(range(n)) or len(lcp) != n or lcp[0] != 0:
                return False
            for i in range(1, n):
                a, b = text[sa[i - 1]:], text[sa[i]:]
                if not a < b:
                    return False
                # binary search for the common prefix length
                lo, hi = 0, min(len(a), len(b))
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if a[:mid] == b[:mid]:
                        lo = mid
                    else:
                        hi = mid - 1
                if lcp[i] != lo:
                    return False
            s = r['repeated']
            return len(s) == max(lcp) and (len(s) == 0 or occurrences(text, s) >= 2)
        return chk
    for text in ('a' * n, 'ab' * (n // 2), rand_str(n, 'abc'), rand_str(n, 'abcdefghijklmnopqrstuvwxyz')):
        out.append(({'task': 'suffix', 'text': text}, check(text)))
    return out


def aho_big():
    out = []
    # dense: patterns a, aa, ..., a^446 (total length 99681) on 100 texts of 2000 'a'
    pats = ['a' * k for k in range(1, 447)]
    texts = ['a' * 2000 for _ in range(100)]
    row = [max(0, 2000 - k + 1) for k in range(1, 447)]
    out.append(({'task': 'aho', 'patterns': pats, 'texts': texts}, eq({'counts': [row] * 100})))
    # 10000 patterns (many duplicates), random text
    pats2 = [rand_str(random.randint(1, 10), 'ab') for _ in range(10000)]
    txts2 = [rand_str(2000, 'ab') for _ in range(5)]
    cache = {}
    exp = []
    for t in txts2:
        row = []
        for p in pats2:
            key = (t, p)
            if key not in cache:
                cache[key] = len(positions_fast(t, p))
            row.append(cache[key])
        exp.append(row)
    out.append(({'task': 'aho', 'patterns': pats2, 'texts': txts2}, eq({'counts': exp})))
    # one long pattern, one long text
    out.append(({'task': 'aho', 'patterns': ['ab' * 50000], 'texts': ['ab' * 100000]}, eq({'counts': [[50001]]})))
    return out


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------
def run_group(name, cases):
    global failures, total
    reqs = [c[0] for c in cases]
    try:
        resps, dt = run_batch(reqs, timeout=60)
    except Exception as e:  # process failure = whole batch fails
        print('FAIL %-22s batch error: %s' % (name, e))
        failures += len(cases)
        total += len(cases)
        return
    bad = 0
    for req, resp, (_, chk) in zip(reqs, resps, cases):
        try:
            ok = chk(resp)
        except Exception:
            ok = False
        if not ok:
            bad += 1
            if bad <= 3:
                print('   wrong answer for', json.dumps(req)[:150], '->', json.dumps(resp)[:150])
    failures += bad
    total += len(cases)
    print('%s %-22s %4d cases, %4d wrong, java batch %.2fs' % ('PASS' if bad == 0 else 'FAIL', name, len(cases), bad, dt))


def mixed_group():
    """one process, different tasks interleaved and repeated: catches state left over between requests"""
    pool = []
    pool += [c for c in lcs_group()[:30]]
    pool += [c for c in merge_group()[:30]]
    pool += [c for c in tree_group()[:30]]
    pool += [c for c in search_group('naive')[:20]]
    pool += [c for c in search_group('kmp')[:20]]
    pool += [c for c in search_group('rk')[:20]]
    pool += [c for c in suffix_group()[:30]]
    pool += [c for c in aho_group()[:30]]
    random.shuffle(pool)
    return pool + pool


def main():
    compile_java()
    groups = [
        ('lcs small', lcs_group()), ('merge small', merge_group()), ('tree small', tree_group()),
        ('naive small', search_group('naive')), ('kmp small', search_group('kmp')),
        ('rk small', search_group('rk')), ('rk collisions', rk_extra()),
        ('suffix small', suffix_group()), ('aho small', aho_group()),
        ('mixed + repeated', mixed_group()),
        ('lcs 1000x1000', lcs_big()), ('merge n=200', merge_big()), ('tree n=100000', tree_big()),
        ('search limits', search_big()), ('suffix n=50000', suffix_big()), ('aho dense/limits', aho_big()),
    ]
    for name, cases in groups:
        run_group(name, cases)
    print('\nTOTAL: %d cases, %d failed' % (total, failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
