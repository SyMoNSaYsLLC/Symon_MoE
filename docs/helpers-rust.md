# Rust Helpers Reference

**Workspace:** `helpers/rust/`  
**Requires:** Rust ≥ 1.75 (`rustup install stable`)

## Build

```bash
cd helpers/rust
cargo build --release
```

Binaries are placed under `helpers/rust/target/release/`.

---

## gguf_parser

**Crate:** `helpers/rust/gguf_parser`

An async GGUF binary parser that reads metadata KV pairs and tensor descriptors.

### CLI

```
Usage: gguf_parser [OPTIONS] <PATH>

Arguments:
  <PATH>          Path to a .gguf file

Options:
  --tensors       Print tensor list instead of metadata
  --key <KEY>     Print a single metadata value by key
  --json          Output as JSON (default: human-readable)
  -h, --help      Print help
```

**Examples**

```bash
# Print all metadata
./target/release/gguf_parser model.gguf

# Print tensor list as JSON
./target/release/gguf_parser model.gguf --tensors --json

# Read a single key
./target/release/gguf_parser model.gguf --key general.architecture
```

### Library API

```rust
use gguf_parser::GGUFReader;

#[tokio::main]
async fn main() {
    let reader = GGUFReader::open("model.gguf").await.unwrap();
    let meta = reader.metadata();
    let tensors = reader.tensors();
    println!("Architecture: {}", meta.get_str("general.architecture").unwrap_or("?"));
}
```

---

## ollama_client

**Crate:** `helpers/rust/ollama_client`

An async HTTP client for the Ollama REST API (uses `reqwest` + `tokio`).

### CLI

```
Usage: ollama_client <COMMAND>

Commands:
  list            List models in a running Ollama instance
  pull <NAME>     Pull a model from the Ollama registry
  delete <NAME>   Delete a model from the local Ollama instance
  chat <MODEL>    Interactive chat with a model (reads prompt from stdin)
  generate        One-shot text generation (--model, --prompt flags)
```

**Examples**

```bash
# List available models
./target/release/ollama_client list

# Pull llama3
./target/release/ollama_client pull llama3:8b

# One-shot generation
./target/release/ollama_client generate --model llama3 --prompt "Hello!"

# Interactive chat
echo "What is a tensor?" | ./target/release/ollama_client chat llama3
```

### Library API

```rust
use ollama_client::OllamaClient;

#[tokio::main]
async fn main() {
    let client = OllamaClient::new("http://localhost:11434");
    let models = client.list_models().await.unwrap();
    let resp = client.generate("llama3", "What is backpropagation?").await.unwrap();
    println!("{}", resp.response);
}
```

---

## m3u_parser

**Crate:** `helpers/rust/m3u_parser`

An async M3U/M3U8 playlist parser and URL fetcher.

### CLI

```
Usage: m3u_parser [OPTIONS] <INPUT>

Arguments:
  <INPUT>         URL or path to M3U/M3U8 playlist file

Options:
  --filter <GROUP>    Filter channels by group-title attribute
  --json              Output as JSON (default: human-readable table)
  --count             Print channel count and group list only
  -h, --help          Print help
```

**Examples**

```bash
# Parse a local M3U file
./target/release/m3u_parser playlist.m3u

# Fetch and parse a remote playlist, output JSON
./target/release/m3u_parser https://example.com/playlist.m3u --json

# Filter by group
./target/release/m3u_parser playlist.m3u --filter "Sports"

# Summary only
./target/release/m3u_parser playlist.m3u --count
```

### Library API

```rust
use m3u_parser::{fetch_and_parse, parse_m3u};

#[tokio::main]
async fn main() {
    // From URL
    let channels = fetch_and_parse("https://example.com/list.m3u").await.unwrap();
    // From string
    let channels = parse_m3u("#EXTM3U\n#EXTINF:-1,Test\nhttps://stream.url");
    for ch in &channels {
        println!("{}: {}", ch.name, ch.url);
    }
}
```
