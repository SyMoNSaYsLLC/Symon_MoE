package com.symoneural;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/**
 * SymPyBridge — JNI/subprocess bridge to run Python SymPy evaluations from the JVM.
 *
 * <p>Invokes the {@code helpers/python/sympy_calc.py} script as a subprocess and
 * captures its JSON output.  This avoids a JNI native library requirement while
 * still providing full SymPy capabilities from Java/Android code.
 *
 * <p>Usage:
 * <pre>{@code
 *   SymPyBridge bridge = new SymPyBridge();
 *   String json = bridge.evaluate("derivative", "x**3 + 2*x", Map.of("var", "x"));
 *   System.out.println(json);
 * }</pre>
 */
public class SymPyBridge {

    private final String  pythonExecutable;
    private final Path    scriptPath;
    private final int     timeoutSeconds;

    // ------------------------------------------------------------------ //
    // Constructor
    // ------------------------------------------------------------------ //

    /**
     * Create a bridge using the default Python interpreter and the script
     * at {@code helpers/python/sympy_calc.py} relative to the repository root.
     */
    public SymPyBridge() {
        this(detectPython(), detectScriptPath(), 30);
    }

    public SymPyBridge(String pythonExecutable, Path scriptPath, int timeoutSeconds) {
        this.pythonExecutable = pythonExecutable;
        this.scriptPath       = scriptPath;
        this.timeoutSeconds   = timeoutSeconds;
    }

    // ------------------------------------------------------------------ //
    // Public API
    // ------------------------------------------------------------------ //

    /**
     * Evaluate a SymPy expression.
     *
     * @param mode    One of: derivative, integral, limit, ode, numeric
     * @param expr    The expression string (e.g. "x**2 + sin(x)")
     * @param options Additional CLI options (key → value pairs, e.g. "var" → "x")
     * @return        Raw JSON string from sympy_calc.py
     */
    public String evaluate(String mode, String expr, Map<String, String> options)
            throws IOException, InterruptedException {

        List<String> cmd = new ArrayList<>(List.of(
                pythonExecutable, scriptPath.toString(), mode, expr
        ));
        if (options != null) {
            options.forEach((k, v) -> { cmd.add("--" + k); cmd.add(v); });
        }

        ProcessBuilder pb = new ProcessBuilder(cmd)
                .redirectErrorStream(false);
        Process proc = pb.start();

        // Capture stdout
        CompletableFuture<String> stdoutFuture = CompletableFuture.supplyAsync(() -> {
            try (BufferedReader br = new BufferedReader(
                    new InputStreamReader(proc.getInputStream()))) {
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) sb.append(line).append('\n');
                return sb.toString().trim();
            } catch (IOException e) {
                return "";
            }
        });

        // Capture stderr
        CompletableFuture<String> stderrFuture = CompletableFuture.supplyAsync(() -> {
            try (BufferedReader br = new BufferedReader(
                    new InputStreamReader(proc.getErrorStream()))) {
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) sb.append(line).append('\n');
                return sb.toString().trim();
            } catch (IOException e) {
                return "";
            }
        });

        boolean finished = proc.waitFor(timeoutSeconds, TimeUnit.SECONDS);
        if (!finished) {
            proc.destroyForcibly();
            throw new IOException("sympy_calc.py timed out after " + timeoutSeconds + "s");
        }

        String stdout = stdoutFuture.join();
        String stderr = stderrFuture.join();

        if (proc.exitValue() != 0) {
            throw new IOException("sympy_calc.py failed (exit " + proc.exitValue() + "): " + stderr);
        }
        return stdout;
    }

    /**
     * Convenience overload with no extra options.
     */
    public String evaluate(String mode, String expr) throws IOException, InterruptedException {
        return evaluate(mode, expr, null);
    }

    // ------------------------------------------------------------------ //
    // Helpers
    // ------------------------------------------------------------------ //

    private static String detectPython() {
        for (String candidate : List.of("python3", "python")) {
            try {
                Process p = new ProcessBuilder(candidate, "--version").start();
                if (p.waitFor(5, TimeUnit.SECONDS) && p.exitValue() == 0) return candidate;
            } catch (Exception ignored) {}
        }
        return "python3";
    }

    private static Path detectScriptPath() {
        // Try to locate relative to the JAR or CWD
        Path candidate = Path.of("helpers", "python", "sympy_calc.py");
        if (Files.exists(candidate)) return candidate.toAbsolutePath();
        // Try parent directory (running from helpers/java/)
        candidate = Path.of("..", "python", "sympy_calc.py");
        if (Files.exists(candidate)) return candidate.toAbsolutePath();
        // Return default and let the subprocess report an error
        return Path.of("helpers/python/sympy_calc.py").toAbsolutePath();
    }

    // ------------------------------------------------------------------ //
    // CLI
    // ------------------------------------------------------------------ //

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("Usage: SymPyBridge <mode> <expr> [--key value ...]");
            System.exit(1);
        }
        SymPyBridge bridge = new SymPyBridge();
        Map<String, String> opts = new LinkedHashMap<>();
        for (int i = 2; i < args.length - 1; i += 2) {
            opts.put(args[i].replaceFirst("^--", ""), args[i + 1]);
        }
        String result = bridge.evaluate(args[0], args[1], opts);
        System.out.println(result);
    }
}
