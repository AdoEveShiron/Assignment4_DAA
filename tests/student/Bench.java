import java.util.*;

/**
 * Benchmark naive / KMP / exact Rabin-Karp on identical inputs.
 *
 * Build and run from the repository root (after Java/source is compiled into Java/build):
 *   javac --release 17 -cp Java/build -d Java/build tests/student/Bench.java
 *   java -Xmx384m -cp Java/build Bench
 *
 * Timing scope: one call Algorithms.xxx(input) on an already parsed input map, including
 * building the result list. JSON parsing/printing and JVM start are NOT measured.
 * Warm-up: WARMUP untimed calls per (algorithm, case) before the measured runs, so the JIT has
 * compiled the methods. One "run" = REPS back-to-back calls timed together with System.nanoTime(),
 * reported as microseconds per call. 3 runs per row, median of the 3 is reported.
 */
public class Bench {
    static final int WARMUP = 3000;
    static final int REPS = 200;
    static final int RUNS = 3;
    static final long SEED = 12345L;

    interface Alg { Map<String, Object> run(Map<String, Object> in); }

    static String randomText(Random rnd, int n, String alphabet) {
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) sb.append(alphabet.charAt(rnd.nextInt(alphabet.length())));
        return sb.toString();
    }

    static String repeat(char c, int k) {
        char[] a = new char[k];
        Arrays.fill(a, c);
        return new String(a);
    }

    /** independent reference used only to check the answers (String.startsWith is fine in a test) */
    static List<Integer> reference(String t, String p) {
        List<Integer> r = new ArrayList<>();
        for (int i = 0; i + p.length() <= t.length(); i++) if (t.startsWith(p, i)) r.add(i);
        return r;
    }

    static double median(double[] a) {
        double[] c = a.clone();
        Arrays.sort(c);
        return c[c.length / 2];
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) {
        int[][] sizes = {{500, 50}, {1500, 150}, {3000, 300}}; // n, m (all <= 3000, common domain)
        String[] caseNames = {"random", "repetitive-nomatch", "repetitive-allmatch"};
        String[] algNames = {"naive", "kmp", "rk"};
        Alg[] algs = {Algorithms::naive, Algorithms::kmp, Algorithms::rk};

        System.out.println("java.version=" + System.getProperty("java.version")
                + " os=" + System.getProperty("os.name") + " " + System.getProperty("os.arch")
                + " cpus=" + Runtime.getRuntime().availableProcessors()
                + " maxHeapMB=" + Runtime.getRuntime().maxMemory() / (1024 * 1024));
        System.out.println("seed=" + SEED + " warmup=" + WARMUP + " reps/run=" + REPS + " runs=" + RUNS);
        System.out.println();
        System.out.println("|Case|n|m|Seed/generator|Algorithm|Run 1 (us)|Run 2 (us)|Run 3 (us)|Median (us)|Matches z|Correct outputs checked|");
        System.out.println("|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|");

        long sink = 0; // keeps the JIT from dropping results
        for (String cname : caseNames) {
            for (int[] nm : sizes) {
                int n = nm[0], m = nm[1];
                Random rnd = new Random(SEED + n); // seed depends only on size, same for every algorithm
                String text, pattern, gen;
                switch (cname) {
                    case "random":
                        text = randomText(rnd, n, "abcdefghijklmnopqrstuvwxyz");
                        int start = rnd.nextInt(n - m + 1);
                        pattern = text.substring(start, start + m); // substring of the text, so >= 1 match
                        gen = "Random(" + (SEED + n) + "), 26 letters, pattern = text substring";
                        break;
                    case "repetitive-nomatch":
                        text = repeat('a', n);
                        pattern = repeat('a', m - 1) + "b";
                        gen = "text a^n, pattern a^(m-1)b";
                        break;
                    default:
                        text = repeat('a', n);
                        pattern = repeat('a', m);
                        gen = "text a^n, pattern a^m";
                }
                Map<String, Object> in = new HashMap<>();
                in.put("task", "x");
                in.put("text", text);
                in.put("pattern", pattern);

                // correctness first: all three must equal the reference
                List<Integer> ref = reference(text, pattern);
                boolean allOk = true;
                for (Alg a : algs) {
                    if (!ref.equals(a.run(in).get("positions"))) allOk = false;
                }
                if (!allOk) throw new IllegalStateException("outputs differ for " + cname + " n=" + n);

                for (int ai = 0; ai < algs.length; ai++) {
                    Alg alg = algs[ai];
                    for (int w = 0; w < WARMUP; w++) sink += ((List<?>) alg.run(in).get("positions")).size();
                    double[] runs = new double[RUNS];
                    for (int r = 0; r < RUNS; r++) {
                        long t0 = System.nanoTime();
                        for (int k = 0; k < REPS; k++) sink += ((List<?>) alg.run(in).get("positions")).size();
                        long t1 = System.nanoTime();
                        runs[r] = (t1 - t0) / 1000.0 / REPS;
                    }
                    System.out.printf(Locale.ROOT, "|%s|%d|%d|%s|%s|%.1f|%.1f|%.1f|%.1f|%d|yes (= reference)|%n",
                            cname, n, m, gen, algNames[ai], runs[0], runs[1], runs[2], median(runs), ref.size());
                }
            }
        }
        System.out.println();
        System.out.println("sink=" + sink);
    }
}
