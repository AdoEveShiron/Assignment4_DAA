import java.util.*;

/** Assignment 4 algorithms. docs/guide/CONTRACTS.md defines each field and limit. */
public final class Algorithms {

    // ---------------------------------------------------------------
    // helpers
    // ---------------------------------------------------------------

    /** Json.parse gives every number as Long, so convert to int in one place. */
    private static int toInt(Object o) {
        return (int) ((Long) o).longValue();
    }

    private static Map<String, Object> result() {
        return new LinkedHashMap<>();
    }

    // ---------------------------------------------------------------
    // Part 1: LCS
    // ---------------------------------------------------------------

    /**
     * dp[i][j] = length of the LCS of a[0..i) and b[0..j).
     * Row 0 and column 0 are 0 (one of the prefixes is empty).
     */
    static Map<String, Object> lcs(Map<String, Object> input) {
        String a = (String) input.get("a");
        String b = (String) input.get("b");
        int n = a.length(), m = b.length();

        int[][] dp = new int[n + 1][m + 1];
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                if (a.charAt(i - 1) == b.charAt(j - 1)) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                } else {
                    dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
                }
            }
        }

        // walk back from dp[n][m] and collect the matched characters
        StringBuilder sb = new StringBuilder();
        int i = n, j = m;
        while (i > 0 && j > 0) {
            if (a.charAt(i - 1) == b.charAt(j - 1)) {
                sb.append(a.charAt(i - 1));
                i--;
                j--;
            } else if (dp[i - 1][j] >= dp[i][j - 1]) {
                i--;
            } else {
                j--;
            }
        }
        sb.reverse();

        Map<String, Object> res = result();
        res.put("length", (long) dp[n][m]);
        res.put("sequence", sb.toString());
        return res;
    }

    // ---------------------------------------------------------------
    // Part 2: merge adjacent blocks (interval DP)
    // ---------------------------------------------------------------

    /**
     * dp[l][r] = minimum cost to merge blocks l..r into one block.
     * The last merge joins [l,k] and [k+1,r] and costs sum(sizes[l..r]),
     * so dp[l][r] = min over k of dp[l][k] + dp[k+1][r] + sum(l..r).
     */
    static Map<String, Object> merge(Map<String, Object> input) {
        List<?> raw = (List<?>) input.get("sizes");
        int n = raw.size();
        Map<String, Object> res = result();
        if (n <= 1) {
            res.put("cost", 0L);
            res.put("plan", new ArrayList<>());
            return res;
        }

        long[] prefix = new long[n + 1];
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + (Long) raw.get(i);
        }

        long[][] dp = new long[n][n];
        int[][] split = new int[n][n];
        for (int len = 2; len <= n; len++) {
            for (int l = 0; l + len - 1 < n; l++) {
                int r = l + len - 1;
                long sum = prefix[r + 1] - prefix[l];
                long best = Long.MAX_VALUE;
                int bestK = l;
                for (int k = l; k < r; k++) {
                    long c = dp[l][k] + dp[k + 1][r] + sum;
                    if (c < best) {
                        best = c;
                        bestK = k;
                    }
                }
                dp[l][r] = best;
                split[l][r] = bestK;
            }
        }

        // Post-order over the split tree: both children are emitted before
        // their parent, so every merge in the plan has its inputs ready.
        // Recursion depth is at most n-1 <= 199, which is fine.
        List<long[]> plan = new ArrayList<>();
        buildPlan(0, n - 1, split, plan);

        res.put("cost", dp[0][n - 1]);
        res.put("plan", plan);
        return res;
    }

    private static void buildPlan(int l, int r, int[][] split, List<long[]> plan) {
        if (l == r) return;
        int k = split[l][r];
        buildPlan(l, k, split, plan);
        buildPlan(k + 1, r, split, plan);
        plan.add(new long[]{l, k, r});
    }

    // ---------------------------------------------------------------
    // Part 3: maximum weight independent set on a tree
    // ---------------------------------------------------------------

    /**
     * take[v] = best weight in the subtree of v if v is chosen
     * skip[v] = best weight in the subtree of v if v is not chosen
     * take[v] = w[v] + sum skip[child]
     * skip[v] = sum max(take[child], skip[child])
     * Everything is iterative because a chain of 100000 vertices would
     * overflow the Java call stack with a recursive DFS.
     */
    static Map<String, Object> tree(Map<String, Object> input) {
        int n = toInt(input.get("n"));
        Map<String, Object> res = result();
        if (n == 0) {
            res.put("weight", 0L);
            res.put("selected", new ArrayList<>());
            return res;
        }

        List<?> w = (List<?>) input.get("weights");
        List<?> edges = (List<?>) input.get("edges");

        // adjacency in arrays (head/next) to avoid n small lists
        int[] head = new int[n];
        Arrays.fill(head, -1);
        int[] nxt = new int[2 * (n - 1)];
        int[] to = new int[2 * (n - 1)];
        int cnt = 0;
        for (Object eo : edges) {
            List<?> e = (List<?>) eo;
            int u = toInt(e.get(0)), v = toInt(e.get(1));
            to[cnt] = v; nxt[cnt] = head[u]; head[u] = cnt++;
            to[cnt] = u; nxt[cnt] = head[v]; head[v] = cnt++;
        }

        // BFS order from root 0; parents always appear before children
        int[] parent = new int[n];
        int[] order = new int[n];
        parent[0] = -1;
        int qh = 0, qt = 0;
        order[qt++] = 0;
        while (qh < qt) {
            int v = order[qh++];
            for (int e = head[v]; e != -1; e = nxt[e]) {
                int u = to[e];
                if (u != parent[v]) {
                    parent[u] = v;
                    order[qt++] = u;
                }
            }
        }

        long[] take = new long[n];
        long[] skip = new long[n];
        for (int i = 0; i < n; i++) take[i] = (Long) w.get(i);

        // reverse BFS order = children before parents
        for (int i = n - 1; i > 0; i--) {
            int v = order[i];
            int p = parent[v];
            take[p] += skip[v];
            skip[p] += Math.max(take[v], skip[v]);
        }

        // Reconstruction from the root down. A vertex can only be taken if its
        // parent was not taken. Ties go to "skip".
        boolean[] taken = new boolean[n];
        List<Integer> selected = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            int v = order[i];
            boolean parentTaken = parent[v] != -1 && taken[parent[v]];
            if (!parentTaken && take[v] > skip[v]) {
                taken[v] = true;
                selected.add(v);
            }
        }

        res.put("weight", Math.max(take[0], skip[0]));
        res.put("selected", selected);
        return res;
    }

    // ---------------------------------------------------------------
    // Part 4: exact search (naive, KMP, Rabin-Karp)
    // ---------------------------------------------------------------

    /** Empty pattern matches at every boundary 0..n. Shared by all three searches. */
    private static List<Integer> allBoundaries(int n) {
        List<Integer> pos = new ArrayList<>(n + 1);
        for (int i = 0; i <= n; i++) pos.add(i);
        return pos;
    }

    private static Map<String, Object> positions(List<Integer> pos) {
        Map<String, Object> res = result();
        res.put("positions", pos);
        return res;
    }

    static Map<String, Object> naive(Map<String, Object> input) {
        String t = (String) input.get("text");
        String p = (String) input.get("pattern");
        int n = t.length(), m = p.length();
        if (m == 0) return positions(allBoundaries(n));

        List<Integer> pos = new ArrayList<>();
        // last possible start is n-m, so for m>n the loop does not run
        for (int i = 0; i + m <= n; i++) {
            int j = 0;
            while (j < m && t.charAt(i + j) == p.charAt(j)) j++;
            if (j == m) pos.add(i);
        }
        return positions(pos);
    }

    /** pi[i] = length of the longest proper prefix of p[0..i] that is also its suffix. */
    private static int[] prefixFunction(String p) {
        int m = p.length();
        int[] pi = new int[m];
        int k = 0;
        for (int i = 1; i < m; i++) {
            while (k > 0 && p.charAt(i) != p.charAt(k)) k = pi[k - 1];
            if (p.charAt(i) == p.charAt(k)) k++;
            pi[i] = k;
        }
        return pi;
    }

    static Map<String, Object> kmp(Map<String, Object> input) {
        String t = (String) input.get("text");
        String p = (String) input.get("pattern");
        int n = t.length(), m = p.length();
        if (m == 0) return positions(allBoundaries(n));
        if (m > n) return positions(new ArrayList<>());

        int[] pi = prefixFunction(p);
        List<Integer> pos = new ArrayList<>();
        int k = 0; // how many characters of the pattern are currently matched
        for (int i = 0; i < n; i++) {
            while (k > 0 && t.charAt(i) != p.charAt(k)) k = pi[k - 1];
            if (t.charAt(i) == p.charAt(k)) k++;
            if (k == m) {
                pos.add(i - m + 1);
                k = pi[k - 1]; // fall back so overlapping matches are kept
            }
        }
        return positions(pos);
    }

    private static final int RK_BASE = 31;
    private static final int RK_MOD = 101;

    static Map<String, Object> rk(Map<String, Object> input) {
        String t = (String) input.get("text");
        String p = (String) input.get("pattern");
        int n = t.length(), m = p.length();
        if (m == 0) return positions(allBoundaries(n));
        if (m > n) return positions(new ArrayList<>());

        // high = BASE^(m-1) mod MOD, the weight of the leftmost character
        int high = 1;
        for (int i = 1; i < m; i++) high = (high * RK_BASE) % RK_MOD;

        int hp = 0, ht = 0;
        for (int i = 0; i < m; i++) {
            hp = (hp * RK_BASE + p.charAt(i)) % RK_MOD;
            ht = (ht * RK_BASE + t.charAt(i)) % RK_MOD;
        }

        List<Integer> pos = new ArrayList<>();
        for (int i = 0; ; i++) {
            if (hp == ht) {
                // equal hashes are only a candidate, check the characters
                int j = 0;
                while (j < m && t.charAt(i + j) == p.charAt(j)) j++;
                if (j == m) pos.add(i);
            }
            if (i + m >= n) break;
            // drop t[i], shift, add t[i+m]; the +MOD keeps the remainder non-negative
            ht = (ht - t.charAt(i) * high % RK_MOD + RK_MOD) % RK_MOD;
            ht = (ht * RK_BASE + t.charAt(i + m)) % RK_MOD;
        }
        return positions(pos);
    }

    // ---------------------------------------------------------------
    // Part 5: suffix array (prefix doubling) + Kasai LCP
    // ---------------------------------------------------------------

    static Map<String, Object> suffix(Map<String, Object> input) {
        String s = (String) input.get("text");
        int n = s.length();
        Map<String, Object> res = result();
        if (n == 0) {
            res.put("sa", new ArrayList<>());
            res.put("lcp", new ArrayList<>());
            res.put("repeated", "");
            return res;
        }

        int[] sa = buildSuffixArray(s);

        // Kasai: rank is the inverse of sa
        int[] rank = new int[n];
        for (int i = 0; i < n; i++) rank[sa[i]] = i;
        int[] lcp = new int[n];
        int h = 0;
        for (int i = 0; i < n; i++) {
            if (rank[i] > 0) {
                int j = sa[rank[i] - 1];
                while (i + h < n && j + h < n && s.charAt(i + h) == s.charAt(j + h)) h++;
                lcp[rank[i]] = h;
                if (h > 0) h--; // moving to suffix i+1 loses at most one character
            } else {
                h = 0;
            }
        }

        // the longest repeat is the prefix of length max(lcp) of the suffix at that position
        int bestLen = 0, bestIdx = 0;
        for (int i = 1; i < n; i++) {
            if (lcp[i] > bestLen) {
                bestLen = lcp[i];
                bestIdx = i;
            }
        }
        String repeated = bestLen == 0 ? "" : s.substring(sa[bestIdx], sa[bestIdx] + bestLen);

        List<Integer> saList = new ArrayList<>(n);
        List<Integer> lcpList = new ArrayList<>(n);
        for (int i = 0; i < n; i++) {
            saList.add(sa[i]);
            lcpList.add(lcp[i]);
        }
        res.put("sa", saList);
        res.put("lcp", lcpList);
        res.put("repeated", repeated);
        return res;
    }

    /**
     * Prefix doubling. After the round with length k, rank[i] says how suffix i
     * compares with the others using only its first 2k characters. Each round
     * sorts by the pair (rank[i], rank[i+k]) with two counting-sort passes, so
     * the whole thing is O(n log n). Suffixes that run out of characters get
     * second key -1 (they are smaller than any real continuation), so no
     * sentinel character is added to the text.
     */
    private static int[] buildSuffixArray(String s) {
        int n = s.length();
        int[] sa = new int[n];
        int[] rank = new int[n];
        int[] tmpRank = new int[n];
        int[] sa2 = new int[n];

        // initial sort by the first character (codes are < 128)
        int alphabet = 128;
        int[] cnt = new int[Math.max(alphabet, n) + 1];
        for (int i = 0; i < n; i++) cnt[s.charAt(i)]++;
        for (int i = 1; i < alphabet; i++) cnt[i] += cnt[i - 1];
        for (int i = n - 1; i >= 0; i--) sa[--cnt[s.charAt(i)]] = i;
        rank[sa[0]] = 0;
        int classes = 1;
        for (int i = 1; i < n; i++) {
            if (s.charAt(sa[i]) != s.charAt(sa[i - 1])) classes++;
            rank[sa[i]] = classes - 1;
        }

        for (int k = 1; classes < n; k <<= 1) {
            // order by the second key: suffixes with no second half come first,
            // the others follow in the order of their second half
            int p = 0;
            for (int i = n - k; i < n; i++) sa2[p++] = i;
            for (int i = 0; i < n; i++) {
                if (sa[i] >= k) sa2[p++] = sa[i] - k;
            }

            // stable counting sort by the first key
            Arrays.fill(cnt, 0, classes + 1, 0);
            for (int i = 0; i < n; i++) cnt[rank[i]]++;
            for (int i = 1; i < classes; i++) cnt[i] += cnt[i - 1];
            for (int i = n - 1; i >= 0; i--) sa[--cnt[rank[sa2[i]]]] = sa2[i];

            // recompute ranks from the pairs
            tmpRank[sa[0]] = 0;
            classes = 1;
            for (int i = 1; i < n; i++) {
                int a = sa[i - 1], b = sa[i];
                int a2 = a + k < n ? rank[a + k] : -1;
                int b2 = b + k < n ? rank[b + k] : -1;
                if (rank[a] != rank[b] || a2 != b2) classes++;
                tmpRank[b] = classes - 1;
            }
            int[] swap = rank; rank = tmpRank; tmpRank = swap;
        }
        return sa;
    }

    // ---------------------------------------------------------------
    // Part 6: Aho-Corasick
    // ---------------------------------------------------------------

    private static final int ALPHA = 95;   // printable ASCII 32..126
    private static final int OFFSET = 32;

    static Map<String, Object> aho(Map<String, Object> input) {
        List<?> patterns = (List<?>) input.get("patterns");
        List<?> texts = (List<?>) input.get("texts");
        int p = patterns.size();
        int q = texts.size();

        // upper bound for the number of trie states: total length + root
        int total = 1;
        for (Object o : patterns) total += ((String) o).length();

        int[] go = new int[total * ALPHA]; // 0 means "no edge yet" (root is never a child)
        int[] fail = new int[total];
        int[] termNode = new int[p];       // trie node where pattern i ends
        int states = 1;

        for (int i = 0; i < p; i++) {
            String pat = (String) patterns.get(i);
            int v = 0;
            for (int j = 0; j < pat.length(); j++) {
                int c = pat.charAt(j) - OFFSET;
                if (go[v * ALPHA + c] == 0) go[v * ALPHA + c] = states++;
                v = go[v * ALPHA + c];
            }
            termNode[i] = v; // duplicates share the same node
        }

        // BFS: fail links and full automaton transitions at the same time
        int[] bfs = new int[states];
        int qh = 0, qt = 0;
        for (int c = 0; c < ALPHA; c++) {
            int u = go[c];
            if (u != 0) {
                fail[u] = 0;
                bfs[qt++] = u;
            }
        }
        while (qh < qt) {
            int v = bfs[qh++];
            for (int c = 0; c < ALPHA; c++) {
                int u = go[v * ALPHA + c];
                if (u != 0) {
                    fail[u] = go[fail[v] * ALPHA + c];
                    bfs[qt++] = u;
                } else {
                    go[v * ALPHA + c] = go[fail[v] * ALPHA + c];
                }
            }
        }

        // per text: count visits of each state, then push the counts up the
        // failure links (deepest states first). A state's final number is
        // the number of occurrences of the string it represents.
        List<long[]> rows = new ArrayList<>(q);
        long[] visits = new long[states];
        for (Object to : texts) {
            String t = (String) to;
            Arrays.fill(visits, 0L); // fresh counts for every text
            int v = 0;
            for (int i = 0; i < t.length(); i++) {
                v = go[v * ALPHA + (t.charAt(i) - OFFSET)];
                visits[v]++;
            }
            for (int i = qt - 1; i >= 0; i--) {
                int u = bfs[i];
                visits[fail[u]] += visits[u];
            }
            long[] row = new long[p];
            for (int i = 0; i < p; i++) row[i] = visits[termNode[i]];
            rows.add(row);
        }

        Map<String, Object> res = result();
        res.put("counts", rows);
        return res;
    }
}
