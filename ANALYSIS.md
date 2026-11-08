# Assignment 4 — analysis

Language: Java. Everything below describes the code in `Java/source/Algorithms.java`.

## Environment and commands

| Item | Value |
|---|---|
| Language / runtime | Java, OpenJDK 25.0.2 (compiled with `--release 17`, so it stays Java 17 compatible) |
| OS | macOS 27.2 (build 26B123) |
| Computer / CPU / RAM | MacBook Air 13", Apple M4, 10 CPU cores, 16 GB RAM |
| JVM options | `-Xmx384m` (the same as `tools/run.py`) |

Commands (all from the repository root):

```sh
python tools/run.py --language Java --setup          # compile + ping
python tools/run.py --language Java --check          # 44 public cases + repeated batch
python tests/student/run_tests.py                    # my own tests (compiles Java/source itself)
javac --release 17 -encoding UTF-8 -cp Java/build -d Java/build tests/student/Bench.java
java -Xmx384m -cp Java/build Bench                   # naive / KMP / RK comparison
```

`submission.json` has `"language": "Java"`. The final commit URL is given in Moodle.
Results of the commands above, as actually obtained: `--check` prints PASS for all 44 public cases and for the
repeated batch (45 PASS lines); `run_tests.py` ends with `TOTAL: 3174 cases, 0 failed`
(full output in `tests/student/test_log.txt`).

## Algorithm explanations

Notation: n, m = lengths of text and pattern, z = number of returned starts. "Aux" means memory without input and output.
The JSON parser is the supplied one, so complexity is counted after parsing.

### lcs

- **State.** `dp[i][j]` = length of the longest common subsequence of the prefixes `a[0..i)` and `b[0..j)`. So `i` is how many characters of `a` are used and `j` how many of `b` (not zero-based positions: the character just added is `a[i-1]`).
- **Base cases.** `dp[0][j] = dp[i][0] = 0`, because an empty prefix has only the empty subsequence. This also covers empty inputs: the answer is `dp[n][m] = 0` and the sequence is `""`.
- **Transition.** If `a[i-1] == b[j-1]` then `dp[i][j] = dp[i-1][j-1] + 1`, otherwise `max(dp[i-1][j], dp[i][j-1])`.
- **Order.** Rows i = 1..n, columns j = 1..m. The three cells used (up, left, diagonal) belong to smaller prefixes, so they are already filled.
- **Correctness.** If the last characters are equal, some optimal subsequence can end with that character (matching them never hurts: any optimal answer that leaves one of them unused can be exchanged for one that uses both), so we take 1 + the best of the shorter prefixes. If they differ, at most one of them can be the last character of the answer, so the optimum is the better of dropping `a[i-1]` or dropping `b[j-1]`.
- **Reconstruction.** Start at `(n, m)`. Equal characters: append the character, go diagonally. Otherwise go to the neighbour with the larger value. Ties (`dp[i-1][j] == dp[i][j-1]`) go up (decrease i); both choices are optimal, so any optimal sequence can be returned. The string is reversed at the end.
- **Cost.** Time O((n+1)(m+1)) and memory O((n+1)(m+1)) ints (about 4 MB for 1000×1000). Reconstruction is O(n+m).
- **Boundary test.** `a="tea_time", b="team"` -> length 4. It detects an implementation that looks for a common *substring* (it would give 3, "tea"). `a="", b="abc"` detects a missing base row/column (index -1).

### merge

- **State.** `dp[l][r]` = minimum total cost of merging the original blocks `l..r` into one block, using only merges of adjacent blocks inside this interval. `dp[l][l] = 0`.
- **Transition.** The last merge in the interval joins `[l,k]` and `[k+1,r]` and costs `sum(sizes[l..r])`, which does not depend on k. So `dp[l][r] = min_{l<=k<r} dp[l][k] + dp[k+1][r] + sum(l..r)`. The sum comes from prefix sums in O(1). This is not the matrix-chain formula: here the price of a split is the sum of sizes, not a product of dimensions.
- **Order.** By interval length 2..n. Both sub-intervals are shorter, so they are ready.
- **Correctness.** Every sequence of adjacent merges that ends with one block is a binary tree over the interval; its root is the last merge. The two subtrees are independent problems on `[l,k]` and `[k+1,r]`, and the root cost is fixed by the interval, so taking the optimum for both subtrees and the best k is optimal. The cost of a block is counted every time it takes part in a merge (as in the example `[2,3,4]`: 5 + 9 = 14).
- **Reconstruction.** `split[l][r]` stores the best k. `buildPlan` is a post-order traversal: plan for `[l,k]`, plan for `[k+1,r]`, and then `[l,k,r]`. Children are therefore output before their parent, so when `[l,k,r]` is executed, blocks `[l,k]` and `[k+1,r]` already exist and are adjacent. Total n-1 triples. The recursion depth is at most n-1 ≤ 199. Ties: the first k with the smallest value (strict `<`).
- **Cost.** O(n^3) time (about n^3/6 inner steps), O(n^2) aux (`long[n][n]` and `int[n][n]`). For n ≤ 1 it returns immediately (cost 0, empty plan). Values are `long`: for 200 blocks of 10^9 the optimum is 1 544 000 000 000, which does not fit into an int.
- **Boundary test.** `[10^9]*200` (cost above) detects 32-bit overflow. `[4,1,1,4]` gives 18 with plan `[[1,1,2],[1,2,3],[0,0,3]]`: the plan is valid in chronological order. The `--check` validator and my own checker simulate the plan on the block list, which would reject a plan that lists a parent before a child.

### tree

- **State.** Root the tree at vertex 0. `take[v]` = best weight inside the subtree of v if v is chosen, `skip[v]` = best weight inside the subtree if v is not chosen.
- **Transition.** `take[v] = w[v] + sum skip[c]`, `skip[v] = sum max(take[c], skip[c])` over children c. Leaves: `take = w`, `skip = 0`.
- **Order.** I compute a BFS order from the root (iterative, with arrays `head/next/to` for the adjacency lists). Processing the order backwards visits every child before its parent, which is the same as post-order. A recursive DFS would overflow the stack on a chain of 100000 vertices, so there is no recursion anywhere.
- **Correctness.** Chosen v forces all its children to be skipped; skipped v lets every child independently choose its better option. Subtrees are independent given the decision at v, so the sums are exact. The answer is `max(take[root], skip[root])`. Since `skip` is allowed everywhere, the empty set is always possible and the answer is never negative (all-negative input gives 0). The root choice does not change the optimum because the problem is on the undirected tree.
- **Reconstruction.** Go through the BFS order from the root (parents first). A vertex is chosen if its parent is not chosen and `take[v] > skip[v]`. So the parent decision restricts the child: after a taken parent, the child is forced to "skip". Ties choose skip, which is allowed because an equal value is also optimal. The chosen weight equals the printed weight (the checker verifies the sum of weights of the printed vertices).
- **Cost.** O(n) time and aux (several arrays of size n or 2(n-1)); n = 0 returns at once. Sums use `long`.
- **Boundary test.** Chain of 100000 vertices with random weights in ±10^9 (detects stack overflow) and a star with 99999 leaves of weight 10^9 (the sum 99 999 000 000 000 is far over 2^31). `[-1,-2,-3]` -> weight 0, `selected=[]` (detects a missing "empty set" option).

### naive

- **Idea.** For every start i from 0 to n-m compare `t[i+j]` with `p[j]` for j = 0..m-1.
- **Boundaries.** The last valid start is `n-m` (`i + m <= n` in the loop); the inner loop stops at `j = m-1` (not m). If m > n the loop does not run and the answer is `[]`. For m = 0 the method returns `0..n` before any indexing (n+1 starts, including the end boundary).
- **Overlaps.** Each start is tried independently, so overlapping matches are all found (`aaaaa`, `aaa` -> 0,1,2). Starts are produced in increasing order.
- **Cost.** O(n·m) time worst case (e.g. `a^n` and `a^(m-1)b`), O(1) aux, O(z) output; the empty pattern costs O(n+1).
- **Boundary test.** `text="aaaaa", pattern="aaa"` -> `[0,1,2]` (detects a missed overlap / off-by-one at the last start); `text="abc", pattern="abcd"` -> `[]`.

### kmp

- **State.** `pi[i]` = length of the longest proper prefix of `p[0..i]` that is also a suffix of `p[0..i]`. In the search `k` = the number of pattern characters currently matched ending at text position i.
- **Prefix function.** `pi[0] = 0`; for i ≥ 1 start with `k = pi[i-1]`, while `k > 0` and `p[i] != p[k]` set `k = pi[k-1]`, if `p[i] == p[k]` then `k++`; `pi[i] = k`.
- **Search.** For every text character: on mismatch fall back `k = pi[k-1]` (the matched part keeps its longest border, so no text character is read twice for matching), on equality `k++`. When `k == m` we report `i-m+1` and set `k = pi[m-1]`; this is the fallback after a full match, and it is what keeps overlapping occurrences (e.g. `abababa`/`aba` -> 0,2,4).
- **Correctness.** Invariant: after processing `t[0..i]`, k is the length of the longest prefix of the pattern that is a suffix of `t[0..i]` (and k < m after the fallback). Any shorter candidate match is a border of the current one, so the fallback chain `pi[k-1]`, `pi[pi[k-1]-1]`... enumerates all of them in decreasing order.
- **Cost.** k increases at most once per text character and every fallback decreases it, so the total number of fallbacks is ≤ n: O(n+m+z) time (prefix function O(m)). Aux O(m) (the `pi` array), output O(z). m = 0 returns n+1 boundaries before building `pi`; m > n returns `[]`.
- **Boundary test.** `aaaaa`/`aa` -> `[0,1,2,3]` and a^200000 with a^100000 (100001 matches, runs in the batch of the stress test): detects restarting from 0 after a full match (it would miss overlaps) or quadratic behaviour.

### rk (exact Rabin–Karp)

- **Hash.** Base 31, modulus 101, character code as digit, leftmost character has the highest power: `H(s) = (s[0]*31^(m-1) + ... + s[m-1]) mod 101`. `high = 31^(m-1) mod 101` is computed by a loop in O(m).
- **Rolling update.** From window `t[i..i+m)` to the next one: `h = (h - t[i]*high) mod 101`, then `h = (h*31 + t[i+m]) mod 101`. In Java `%` can give a negative value, so I add 101 before the second `%` (`(h - t[i]*high % 101 + 101) % 101`). Without it the hash becomes negative and later equal hashes are missed. All intermediate values stay below 4000, so `int` is enough.
- **Verification.** Equal hashes are only candidates: the characters are compared one by one and the start is reported only if all m are equal. That is what makes the answer exact with such a small modulus (`ab` and `dj` both hash to 75).
- **Edge cases.** m = 0 -> all n+1 boundaries; m > n -> `[]` (both handled before the first window is built). The loop checks the window at i, and stops when `i+m >= n` so `t[i+m]` is never read out of range.
- **Cost.** O(n + m + c·m) where c is the number of windows with an equal hash. With modulus 101, c is about n/101 extra windows for "random" data, but for repetitive data it can be all windows (e.g. all windows match, `a^n` / `a^m`, then c = z = n-m+1 and the cost is z·m). A bound valid for every input is O(n·m + n + m + 1); it is not linear in the worst case. Aux O(1) beyond the pattern hash (rolling window), output O(z).
- **Boundary test.** `text="abdj", pattern="ab"` -> `[0]`: without verification the answer would be `[0,2]`. My tests also contain 80 other colliding two-character pairs found by brute force (see "Own tests") and `dj`*50 + `ab` with pattern `ab` (every `dj` window at an even position has the same hash as `ab`, so each one is a false candidate).

### suffix (prefix doubling + Kasai)

- **Prefix doubling state.** After the round with length k, `rank[i]` is the class of suffix i when only its first 2k characters (or the whole suffix if it is shorter) are compared; equal strings share a class. Initially (k = 0 -> 1) ranks come from the first character (counting sort over codes < 128).
- **Round.** Sort by the pair `(rank[i], rank[i+k])`, where a suffix with `i+k >= n` has second key -1, so it is smaller than any real continuation: this replaces a sentinel, and no sentinel is ever added to the text. The sort is two counting passes: the order by second key is built directly (first the suffixes i ≥ n-k, then `sa[j]-k` for each `sa[j] ≥ k` in the current sa order), then one stable counting sort by the first key. New ranks: a new class starts whenever the pair of the previous suffix differs. The loop stops when the number of classes is n (all suffixes are different) — at most ⌈log2 n⌉ rounds.
- **Correctness.** If two suffixes differ within 2k characters, comparing `(first k, next k)` characters is the same as comparing the pair of their classes from the previous round. Stable counting sort on the first key keeps the second-key order among equal first keys, i.e. a correct lexicographic sort of pairs.
- **Cost of doubling.** Each round is O(n + classes) = O(n), so O(n log n) in total; aux is a few `int[n]` arrays (sa, sa2, rank, tmpRank, count) = O(n). I used counting sort and not a comparison sort.
- **Kasai.** `rank` = inverse of `sa`; for the suffix i at position `rank[i] > 0` compare with the previous suffix `j = sa[rank[i]-1]`, starting with the length h that is already known. `lcp[rank[i]] = h`. When we go to suffix i+1, the lcp can drop by at most 1 (removing the first character of both suffixes keeps the rest of the common prefix, and the neighbour of i+1 in `sa` is at least as similar), so `h = max(h-1, 0)`. `h` increases at most 2n times in total, so Kasai is O(n). `lcp[0] = 0`.
- **Longest repeat.** A substring that occurs at two starts is a common prefix of two suffixes. Suffixes that share a prefix s are contiguous in `sa`, so two of them are adjacent and their lcp is ≥ |s|. So the longest repeat has length `max(lcp)`, and it is the first `max(lcp)` characters of the suffix `sa[idx]` with the maximal `lcp[idx]`. Overlapping occurrences are allowed (`banana` -> `ana`). If `max(lcp) = 0` the answer is `""`. The first maximum is returned; any other maximum is also valid.
- **Cost.** O(n log n) + O(n) time, O(n) aux. The empty text returns `sa=[]`, `lcp=[]`, `repeated=""` at once. I never create the suffix strings.
- **Boundary test.** `aaaa` -> `sa=[3,2,1,0]`, `lcp=[0,1,2,3]`, `repeated="aaa"` (the worst case for the number of rounds and for Kasai reuse; detects a missing "shorter suffix is smaller" rule); `abcd` -> all lcp 0 and `repeated=""`; `banana` equals the example in the task.

### aho (Aho–Corasick)

- **Trie.** One node per distinct prefix. Alphabet is the 95 printable characters (code − 32). The transition table is a flat `int[(L+1)*95]` (≈ 38 MB for L = 100000, which is within the 384/512 MiB limit); 0 means "no edge" because the root is never a child. `termNode[i]` is the node where pattern i ends. Duplicate patterns end in the same node, so they have separate dictionary positions but share the node and get equal counts.
- **Failure links and automaton.** BFS from the root. `fail[u]` for a child u of v with character c is `go[fail[v]][c]`; for a missing edge `go[v][c]` is copied from `go[fail[v]][c]`. Because `fail[v]` is shallower than v, its row is already complete when v is processed. After the BFS every state has all 95 transitions, so the text is read in one step per character with no fallback loops. Construction: O(L + 95·S + p) time and O(95·S + p) memory.
- **Counting.** For each text, `visits[state]++` after every character. Then, in reverse BFS order (deepest first), `visits[fail[u]] += visits[u]`. After this, `visits[u]` is the number of occurrences of the string of node u in the text, because every occurrence of a longer string that has this one as a suffix also passes through the failure chain. This counts overlaps and suffix patterns (`he` inside `she`) without walking output links per match. `counts[t][i] = visits[termNode[i]]`.
- **Independent texts.** `visits` is cleared with `Arrays.fill` and the start state is the root for every text, so the texts do not influence each other; the repeated text `sheshe` gives the same row twice. A `long` counter avoids overflow in dense cases.
- **Cost per text.** O(|text| + S + p). Total output O(q·p). For p = 0 each text gets an empty row (`[]`), and for no texts the answer is `[]`.
- **Boundary test.** `["he","she","he"]` on `["sheshe","sheshe",""]` -> `[[2,2,2],[2,2,2],[0,0,0]]`: checks the suffix-pattern count, duplicates and reset. A dense test with patterns `a, aa, ..., a^446` on 100 texts of 2000 `a` (total pattern length 99681) finishes in 0.24 s (the whole 3-case batch including the JVM start); walking every match would need about 10^8 steps.

## Own tests

All tests are in `tests/student/run_tests.py`. The script compiles `Java/source`, starts one `java` process per group (one JSONL batch, like the official runs) and compares with oracles that I wrote separately in Python (memoised recursion for LCS, all merge orders for merge, all subsets for tree, `text[i:i+m] == pattern` for searches, `sorted(range(n), key=lambda i: text[i:])` for the suffix array, counting with the same slicing for Aho). Plan, selected set and repeated substring are checked as *witnesses* (they are validated, not compared to one fixed answer), so different optimal answers are accepted. Random generators use `random.seed(4242)`. Command for every row: `python tests/student/run_tests.py`; actual result = the line of `tests/student/test_log.txt`.

|Command|Input or fixture path|Expected result|Actual result / log|What it checks|
|---|---|---|---|---|
|lcs|12 hand cases + 300 random pairs (length ≤ 9, alphabet abc), group "lcs small"|length = oracle, sequence is a subsequence of both|PASS 312 cases, 0 wrong|empty inputs, subsequence vs substring (`tea_time`/`team`), case-sensitivity (`AbC`/`abc`), several optimal answers|
|lcs|two 1000-character strings over `abcd` and `a`*1000 vs `a`*1000, group "lcs 1000x1000"|length = Python DP, valid witness|PASS 2 cases, 0 wrong|limit len(a)·len(b) = 10^6, memory and time|
|merge|8 hand cases (n=0,1, zeros, `[2,3,4]`, `[4,1,1,4]`, 7×10^9, ...) + 200 random (n ≤ 7), group "merge small"|cost = brute force over all orders; plan simulated|PASS 208 cases, 0 wrong|0/1 blocks, zeros, ties, adjacency, chronological order|
|merge|n=200: `[10^9]*200`, random up to 10^9, random 0..3, group "merge n=200"|cost = independent Python O(n^3) DP, plan valid|PASS 3 cases, 0 wrong (java batch 0.04 s)|overflow (cost 1 544 000 000 000), time at the limit|
|tree|9 hand cases + 250 random trees (n ≤ 12; chain/star/random), group "tree small"|weight = best of all subsets, selected valid|PASS 259 cases, 0 wrong|n=0/1, all negative, zeros and ties, edges given in both directions and shuffled|
|tree|n=100000: chain, star, random tree (weights ±10^9) and star with all weights 10^9, group "tree n=100000"|weight = separate iterative Python DP with another root (n-1)|PASS 4 cases, 0 wrong (java batch 0.19 s)|deep chain without recursion, sums above 2^31, root independence|
|naive / kmp / rk|15 hand cases + 300 random each, groups "naive small", "kmp small", "rk small"|positions = `text[i:i+m]==pattern` loop|PASS 315 + 315 + 315 cases, 0 wrong|empty pattern (n+1 starts), empty text, pattern longer, case and punctuation, overlaps|
|rk|80 colliding pairs (equal hash base 31/mod 101, found by brute force over all 2-character strings, includes `ab`/`dj`), `dj`*50+`ab`, 300 random windows, group "rk collisions"|positions = oracle|PASS 381 cases, 0 wrong|every equal-hash candidate is verified, negative remainders normalised|
|kmp / rk / naive|`a`*200000 with `a`*100000 (100001 starts), `a`*99999+`b`, random 200000 over `ab`, empty pattern on 200000, rk 10000×2000 and 10000×(1999+`b`), naive 3000×1500 and 3000×2999+`b`, group "search limits"|positions = Python `str.find` loop|PASS 9 cases, 0 wrong (java batch 0.13 s)|limits of each domain, quadratic cases finish within 20 s|
|suffix|13 hand cases (empty, one char, `aaaa`, `abcd`, `banana`, `aAaA`, `a a a`, ...) + 300 random, group "suffix small"|sa and lcp = sorted real suffixes, repeated has max length and ≥ 2 occurrences|PASS 313 cases, 0 wrong|no sentinel in output, permutation/order, ties among repeats, overlaps|
|suffix|n=50000: `a`*50000, `ab`*25000, random over 3 and 26 letters, group "suffix n=50000"|permutation, every adjacent pair is increasing, lcp by binary search, repeated valid|PASS 4 cases, 0 wrong (java batch 0.14 s)|worst-case number of rounds, speed|
|aho|11 hand cases (empty dictionary/texts/text, duplicates, `he`/`she`, `A` vs `a`, spaces) + 300 random, group "aho small"|counts = slicing oracle for every (text, pattern)|PASS 311 cases, 0 wrong|empty dictionary gives empty rows, duplicates, suffix patterns, overlaps, reset between texts|
|aho|dense (446 patterns × 100 texts), 10000 random patterns with duplicates × 5 texts, one pattern of length 100000, group "aho dense/limits"|counts = formula / `str.find` loop|PASS 3 cases, 0 wrong (java batch 0.14 s)|limits (L = 100000, 10000 patterns), dense matches|
|mixed|a shuffled mix of 210 requests of all 8 commands, sent twice in one process, group "mixed + repeated"|each answer equals its oracle|PASS 420 cases, 0 wrong|no state is kept between requests|
|public|`python tools/run.py --check`|44 cases + 2× batch|45 PASS lines|the official examples|

To check that these tests really detect defects I temporarily broke the code twice and restored it after the runs: (1) removed the character verification in RK -> 117 failed cases (groups "rk small", "rk collisions", "mixed", "search limits"); (2) removed the clearing of `visits` between texts in Aho -> 174 failed cases. Both runs failed as they should, and the final code passes everything.

## Search comparison

**Setup.** Program: `tests/student/Bench.java` (run with the commands above). The generator is `java.util.Random` with seed `12345 + n`; the same text and pattern are given to all three algorithms. Sizes (n, m) = (500, 50), (1500, 150), (3000, 300), all inside the common domain (n, m ≤ 3000). Cases:

- *random*: text of n random lowercase letters (26 symbols); the pattern is a random substring of length m of the text (so there is at least one match).
- *repetitive-nomatch*: text `a`^n, pattern `a`^(m-1)`b` (no match, every window agrees on m-1 characters).
- *repetitive-allmatch*: text `a`^n, pattern `a`^m (every window matches, z = n-m+1).

**Correctness first.** Before timing every (case, size) the program compares the output of naive, KMP and RK with an independent reference that uses `String.startsWith` for every start; the program stops with an exception if they differ. All 9 inputs passed (column "Correct outputs checked").

**Timing scope (the same for all methods).** One call `Algorithms.naive/kmp/rk(map)` with the already parsed input map, including creating the result list. JSON parsing, output printing, JVM start and compilation are excluded. **Warm-up:** 3000 untimed calls per (algorithm, case) so that the JIT compiles the method before measuring. **One run** = 200 consecutive calls timed together with `System.nanoTime`, shown as microseconds per call. 3 runs per row; the median of the 3 runs is reported. Heap `-Xmx384m`. Environment: the table above (Java 25.0.2, MacBook Air 13", Apple M4, 10 CPUs, 16 GB RAM, macOS 27.2).

Raw results of the first program run (`tests/student/bench_run1.txt`), times in µs per call:

|Case|n|m|Seed/generator|Algorithm|Run 1 (us)|Run 2 (us)|Run 3 (us)|Median (us)|Matches z|Correct outputs checked|
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
|random|500|50|Random(12845), 26 letters, pattern = text substring|naive|0.7|0.6|0.6|0.6|1|yes (= reference)|
|random|500|50|Random(12845), 26 letters, pattern = text substring|kmp|5.4|5.4|5.4|5.4|1|yes (= reference)|
|random|500|50|Random(12845), 26 letters, pattern = text substring|rk|3.3|3.2|3.2|3.2|1|yes (= reference)|
|random|1500|150|Random(13845), 26 letters, pattern = text substring|naive|1.9|1.9|1.9|1.9|1|yes (= reference)|
|random|1500|150|Random(13845), 26 letters, pattern = text substring|kmp|2.3|2.6|2.3|2.3|1|yes (= reference)|
|random|1500|150|Random(13845), 26 letters, pattern = text substring|rk|9.7|9.6|9.7|9.7|1|yes (= reference)|
|random|3000|300|Random(15345), 26 letters, pattern = text substring|naive|3.5|3.5|3.6|3.5|1|yes (= reference)|
|random|3000|300|Random(15345), 26 letters, pattern = text substring|kmp|5.0|5.1|5.1|5.1|1|yes (= reference)|
|random|3000|300|Random(15345), 26 letters, pattern = text substring|rk|19.2|19.2|19.2|19.2|1|yes (= reference)|
|repetitive-nomatch|500|50|text a^n, pattern a^(m-1)b|naive|20.0|20.1|20.2|20.1|0|yes (= reference)|
|repetitive-nomatch|500|50|text a^n, pattern a^(m-1)b|kmp|1.9|1.9|1.9|1.9|0|yes (= reference)|
|repetitive-nomatch|500|50|text a^n, pattern a^(m-1)b|rk|3.1|3.1|3.1|3.1|0|yes (= reference)|
|repetitive-nomatch|1500|150|text a^n, pattern a^(m-1)b|naive|184.3|183.1|178.0|183.1|0|yes (= reference)|
|repetitive-nomatch|1500|150|text a^n, pattern a^(m-1)b|kmp|5.4|5.4|5.4|5.4|0|yes (= reference)|
|repetitive-nomatch|1500|150|text a^n, pattern a^(m-1)b|rk|9.4|10.5|9.3|9.4|0|yes (= reference)|
|repetitive-nomatch|3000|300|text a^n, pattern a^(m-1)b|naive|725.2|722.5|725.8|725.2|0|yes (= reference)|
|repetitive-nomatch|3000|300|text a^n, pattern a^(m-1)b|kmp|10.7|10.0|10.4|10.4|0|yes (= reference)|
|repetitive-nomatch|3000|300|text a^n, pattern a^(m-1)b|rk|18.8|19.0|18.8|18.8|0|yes (= reference)|
|repetitive-allmatch|500|50|text a^n, pattern a^m|naive|21.1|20.9|20.8|20.9|451|yes (= reference)|
|repetitive-allmatch|500|50|text a^n, pattern a^m|kmp|3.0|2.8|2.8|2.8|451|yes (= reference)|
|repetitive-allmatch|500|50|text a^n, pattern a^m|rk|22.5|22.4|22.4|22.4|451|yes (= reference)|
|repetitive-allmatch|1500|150|text a^n, pattern a^m|naive|191.2|191.6|191.6|191.6|1351|yes (= reference)|
|repetitive-allmatch|1500|150|text a^n, pattern a^m|kmp|6.5|6.1|6.0|6.1|1351|yes (= reference)|
|repetitive-allmatch|1500|150|text a^n, pattern a^m|rk|191.4|192.2|192.2|192.2|1351|yes (= reference)|
|repetitive-allmatch|3000|300|text a^n, pattern a^m|naive|734.8|733.0|733.8|733.8|2701|yes (= reference)|
|repetitive-allmatch|3000|300|text a^n, pattern a^m|kmp|13.5|11.6|11.7|11.7|2701|yes (= reference)|
|repetitive-allmatch|3000|300|text a^n, pattern a^m|rk|738.2|738.0|739.4|738.2|2701|yes (= reference)|

I ran the whole program a second time (`tests/student/bench_run2.txt`) to see how stable the numbers are. Medians of the second run, µs per call:

|Case|n|m|naive|kmp|rk|
|---|---:|---:|---:|---:|---:|
|random|500|50|0.8|5.5|3.3|
|random|1500|150|2.0|2.5|9.6|
|random|3000|300|3.5|5.1|19.2|
|repetitive-nomatch|500|50|20.1|1.9|3.1|
|repetitive-nomatch|1500|150|181.6|5.5|9.5|
|repetitive-nomatch|3000|300|726.8|10.6|18.8|
|repetitive-allmatch|500|50|20.9|2.9|22.4|
|repetitive-allmatch|1500|150|193.9|6.4|192.6|
|repetitive-allmatch|3000|300|743.5|11.9|741.8|

**Observations.**

- *repetitive-nomatch.* Naive is clearly the slowest and grows like n·m: 20.1 -> 183.1 -> 725.2 µs, while n·m grows 9 and then 4 times (the measured ratios are 9.1 and 4.0). KMP (1.9 -> 5.4 -> 10.4 µs) and RK (3.1 -> 9.4 -> 18.8 µs) grow about linearly with n. RK is fast here because the hash of `a`^(m-1)`b` differs from the hash of `a`^m, so there are almost no candidate windows. KMP is about 70 times faster than naive at n = 3000.
- *repetitive-allmatch.* Now RK is as slow as naive (RK 22.4 -> 192.2 -> 738.2 µs, naive 20.9 -> 191.6 -> 733.8 µs) and KMP is about 63 times faster at n = 3000 (11.7 µs). The reason is the candidate term c·m in the RK bound: every window has equal hash and every candidate is verified over all m characters, so c = z and the work is z·m. This is the quadratic case that the rubric mentions: RK is not linear in the worst case.
- *random.* All three need only a few microseconds, and here naive is the fastest (0.6, 1.9, 3.5 µs), because on random 26-letter text almost every window fails on the first or second character, so naive reads about n characters and does no preprocessing. KMP (5.4, 2.3, 5.1 µs) also reads about n characters but first builds the prefix table of size m. RK is the slowest (3.2, 9.7, 19.2 µs) and grows with n, which is consistent with a modulo operation for every text character, but I did not profile it, so this explanation is a hypothesis. The KMP value for n = 500 (5.4 µs) is larger than for n = 1500 (2.3 µs); I did not investigate this and treat it as an effect of such tiny run times (JIT/timer behaviour), not as a property of the algorithm. These differences are of a few microseconds, so I do not draw conclusions about the algorithms from the random case.
- Run-to-run variation on this machine is small: the medians of the two program runs differ by at most about 1.3% for the naive and RK cases with n = 3000 (for example naive allmatch n = 3000: 733.8 and 743.5 µs; RK allmatch n = 3000: 738.2 and 741.8 µs), and the ordering of the methods is the same in both runs. Only the sub-microsecond random cases differ noticeably in relative terms (naive n = 500: 0.6 and 0.8 µs).
- These timings show how the three programs behave on these inputs; they do **not** prove an asymptotic complexity. The bounds come from the analysis above (n·m for naive, n+m+z for KMP, n+m+c·m for RK) and the measurements only agree with them on three sizes.
- **Effect of the small modulus in RK.** With modulus 101 about one window in 101 shares the pattern hash by chance even when the text differs, so verification has to run often (for an input of 3000 random windows I would expect about 30 false candidates, an estimate under the assumption that hashes are roughly uniform; I did not count them). Each false candidate usually fails after one or two characters, so on random text this costs little, but on repetitive input a false candidate can run for almost m characters. The collision pairs in the tests (`ab`/`dj` and 80 others) show that verification is mandatory: without it the answer is wrong. This is a property of this deliberately small laboratory modulus, and I do not claim that every production hash (large 64-bit modulus, random base) behaves the same way: there collisions are far rarer, and the cost is dominated by the match count z rather than by false candidates.
- The known collision `ab`/`dj` is a correctness test in the public set and in my group "rk collisions" (both pass).

## Sources and AI assistance

- **My own work:** I designed and wrote the Java implementation in `Java/source/Algorithms.java` and the algorithm explanations in this file myself, from the assignment text and the lecture material.
- **AI assistance (limited to testing):** I used an AI assistant (Claude, Anthropic) only to help with the testing side of the work: the test script `tests/student/run_tests.py` (with the independent Python oracles), the benchmark program `tests/student/Bench.java`, and help with wording/formatting of the test and benchmark parts of this file. The AI did not write the algorithm implementation.
- **Verification:** I ran all commands myself on my own computer (MacBook Air 13", Apple M4) and the numbers in this file are copied from the real output in `tests/student/test_log.txt`, `bench_run1.txt` and `bench_run2.txt`. Correctness was checked with the public checks (44 cases, the batch twice in one process), my own test script against independent oracles, two deliberate bug injections that the tests detected, and the benchmark's comparison against a `startsWith` reference.
- **Sources:** the assignment text and notes in `docs/` (contracts, rubric, algorithm clarifications), and the lecture material of weeks 8-10 (DP patterns, KMP/hashing, suffix arrays/Kasai/Aho-Corasick). No code from other repositories was used. The JSON transport (`Json.java`, `Main.java`) is the supplied one and was not changed.
