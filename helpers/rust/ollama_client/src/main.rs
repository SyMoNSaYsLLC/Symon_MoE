//! ollama_client — async Rust client for the Ollama REST API
//!
//! Supports `/api/generate`, `/api/chat`, and `/api/embeddings` with
//! streaming responses.

use futures_util::StreamExt;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use thiserror::Error;

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

#[derive(Error, Debug)]
pub enum OllamaError {
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
}

// ---------------------------------------------------------------------------
// Request / Response types
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize)]
pub struct GenerateRequest {
    pub model:   String,
    pub prompt:  String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub system:  Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub options: Option<serde_json::Value>,
    pub stream:  bool,
}

#[derive(Debug, Deserialize)]
pub struct GenerateResponse {
    pub model:    String,
    pub response: String,
    pub done:     bool,
    #[serde(default)]
    pub context:  Vec<i64>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatMessage {
    pub role:    String,   // "system" | "user" | "assistant"
    pub content: String,
}

#[derive(Debug, Serialize)]
pub struct ChatRequest {
    pub model:    String,
    pub messages: Vec<ChatMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub options:  Option<serde_json::Value>,
    pub stream:   bool,
}

#[derive(Debug, Deserialize)]
pub struct ChatResponse {
    pub model:   String,
    pub message: ChatMessage,
    pub done:    bool,
}

#[derive(Debug, Serialize)]
pub struct EmbedRequest {
    pub model:  String,
    pub prompt: String,
}

#[derive(Debug, Deserialize)]
pub struct EmbedResponse {
    pub embedding: Vec<f64>,
}

#[derive(Debug, Deserialize)]
pub struct ModelInfo {
    pub name:       String,
    pub modified_at: Option<String>,
    pub size:       Option<u64>,
}

#[derive(Debug, Deserialize)]
struct TagsResponse {
    models: Vec<ModelInfo>,
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

pub struct OllamaClient {
    base_url: String,
    http:     Client,
}

impl OllamaClient {
    /// Create a new client for the given base URL (e.g. `http://localhost:11434`).
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into().trim_end_matches('/').to_owned(),
            http:     Client::new(),
        }
    }

    /// List models available in the Ollama instance.
    pub async fn list_models(&self) -> Result<Vec<ModelInfo>, OllamaError> {
        let resp: TagsResponse = self
            .http
            .get(format!("{}/api/tags", self.base_url))
            .send()
            .await?
            .json()
            .await?;
        Ok(resp.models)
    }

    /// Generate a completion (non-streaming).
    pub async fn generate(
        &self,
        model: impl Into<String>,
        prompt: impl Into<String>,
        options: Option<serde_json::Value>,
    ) -> Result<String, OllamaError> {
        let req = GenerateRequest {
            model:   model.into(),
            prompt:  prompt.into(),
            system:  None,
            options,
            stream:  false,
        };
        let resp: GenerateResponse = self
            .http
            .post(format!("{}/api/generate", self.base_url))
            .json(&req)
            .send()
            .await?
            .json()
            .await?;
        Ok(resp.response)
    }

    /// Stream a completion, calling *on_token* for each partial response token.
    pub async fn generate_stream<F>(
        &self,
        model: impl Into<String>,
        prompt: impl Into<String>,
        options: Option<serde_json::Value>,
        mut on_token: F,
    ) -> Result<(), OllamaError>
    where
        F: FnMut(String),
    {
        let req = GenerateRequest {
            model:   model.into(),
            prompt:  prompt.into(),
            system:  None,
            options,
            stream:  true,
        };
        let mut stream = self
            .http
            .post(format!("{}/api/generate", self.base_url))
            .json(&req)
            .send()
            .await?
            .bytes_stream();

        while let Some(chunk) = stream.next().await {
            let bytes = chunk?;
            for line in bytes.split(|&b| b == b'\n') {
                if line.is_empty() {
                    continue;
                }
                let resp: GenerateResponse = serde_json::from_slice(line)?;
                on_token(resp.response);
                if resp.done {
                    return Ok(());
                }
            }
        }
        Ok(())
    }

    /// Send a chat message list (non-streaming).
    pub async fn chat(
        &self,
        model: impl Into<String>,
        messages: Vec<ChatMessage>,
        options: Option<serde_json::Value>,
    ) -> Result<ChatMessage, OllamaError> {
        let req = ChatRequest { model: model.into(), messages, options, stream: false };
        let resp: ChatResponse = self
            .http
            .post(format!("{}/api/chat", self.base_url))
            .json(&req)
            .send()
            .await?
            .json()
            .await?;
        Ok(resp.message)
    }

    /// Get an embedding vector for a prompt.
    pub async fn embeddings(
        &self,
        model: impl Into<String>,
        prompt: impl Into<String>,
    ) -> Result<Vec<f64>, OllamaError> {
        let req = EmbedRequest { model: model.into(), prompt: prompt.into() };
        let resp: EmbedResponse = self
            .http
            .post(format!("{}/api/embeddings", self.base_url))
            .json(&req)
            .send()
            .await?
            .json()
            .await?;
        Ok(resp.embedding)
    }
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: ollama_client <base_url> <model> <prompt>");
        std::process::exit(1);
    }
    let client = OllamaClient::new(&args[1]);
    let result = client.generate(&args[2], &args[3], None).await;
    match result {
        Ok(text) => println!("{text}"),
        Err(e)   => { eprintln!("Error: {e}"); std::process::exit(1); }
    }
}
