# Java Helpers Reference

**Module:** `helpers/java/`  
**Requires:** Java 17+ and Maven 3.8+

## Build

```bash
cd helpers/java
mvn package -q
```

The fat JAR is placed at `target/symoneural-helpers-0.1.0-jar-with-dependencies.jar`.

---

## GGUFMetaReader

Read and print GGUF file metadata from the JVM.

### CLI

```
Usage: java -cp target/symoneural-helpers-*.jar com.symoneural.GGUFMetaReader [OPTIONS] <path>

Arguments:
  <path>              Path to a .gguf file

Options:
  --key <KEY>         Read a single metadata key
  --tensors           List tensors instead of metadata
  --json              Output as JSON
```

**Examples**

```bash
JAR=target/symoneural-helpers-0.1.0-jar-with-dependencies.jar

# Read all metadata
java -cp $JAR com.symoneural.GGUFMetaReader model.gguf

# Read a specific key
java -cp $JAR com.symoneural.GGUFMetaReader model.gguf --key general.name

# List tensors as JSON
java -cp $JAR com.symoneural.GGUFMetaReader model.gguf --tensors --json
```

### Library API

```java
import com.symoneural.GGUFMetaReader;

GGUFMetaReader reader = new GGUFMetaReader("model.gguf");
Map<String, Object> meta = reader.readMetadata();
List<Map<String, Object>> tensors = reader.listTensors();
System.out.println(meta.get("general.architecture"));
```

---

## OllamaClient

Java HTTP client for the Ollama REST API (backed by OkHttp3).

### CLI

```
Usage: java -cp <JAR> com.symoneural.OllamaClient <COMMAND> [OPTIONS]

Commands:
  list                     List models in Ollama
  pull <model>             Pull a model
  delete <model>           Delete a model
  generate --model <M> --prompt <P>  One-shot text generation
  chat --model <M>         Interactive chat (reads lines from stdin)

Options:
  --base-url <URL>         Ollama base URL (default: http://localhost:11434)
```

**Examples**

```bash
JAR=target/symoneural-helpers-0.1.0-jar-with-dependencies.jar

# List models
java -cp $JAR com.symoneural.OllamaClient list

# Generate text
java -cp $JAR com.symoneural.OllamaClient generate --model llama3 --prompt "What is a neural network?"

# Pull a model
java -cp $JAR com.symoneural.OllamaClient pull codellama:7b
```

### Library API

```java
import com.symoneural.OllamaClient;

OllamaClient client = new OllamaClient("http://localhost:11434");
List<String> models = client.listModels();
String response = client.generate("llama3", "Explain softmax.");
System.out.println(response);
```

---

## SymPyBridge

Subprocess bridge to run Python SymPy calculations from the JVM.

### CLI

```
Usage: java -cp <JAR> com.symoneural.SymPyBridge <MODE> <EXPR> [OPTIONS]

Arguments:
  MODE     One of: derivative, integral, limit, ode, numeric
  EXPR     Expression string (SymPy syntax)

Options:
  --var <V>       Variable name (default: x)
  --order <N>     Derivative order (default: 1)
  --lower <L>     Integral lower bound
  --upper <U>     Integral upper bound
  --point <P>     Limit point (default: 0)
  --direction <D> Limit direction: +, -, +- (default: +)
  --precision <N> Numeric precision digits (default: 15)
```

**Examples**

```bash
JAR=target/symoneural-helpers-0.1.0-jar-with-dependencies.jar

# Derivative
java -cp $JAR com.symoneural.SymPyBridge derivative "x**3 + 2*x"

# Definite integral
java -cp $JAR com.symoneural.SymPyBridge integral "sin(x)" --lower 0 --upper pi

# Limit
java -cp $JAR com.symoneural.SymPyBridge limit "sin(x)/x" --point 0 --direction +-
```

### Library API

```java
import com.symoneural.SymPyBridge;

SymPyBridge bridge = new SymPyBridge();
Map<String, String> result = bridge.derivative("x**3 + 2*x", "x", 1);
System.out.println(result.get("latex"));   // 3 x^{2} + 2
System.out.println(result.get("numeric")); // 3*x**2 + 2
```

> **Note:** Requires Python 3 and `sympy` installed in the system Python environment.
> The bridge spawns `helpers/python/sympy_calc.py` as a subprocess.
