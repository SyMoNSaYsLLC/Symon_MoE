//! gguf_parser — async GGUF file parser
//!
//! Reads the metadata KV section and tensor info table from a GGUF v1/v2/v3
//! binary file.  Tensor data is not loaded into memory; only offsets are
//! recorded so callers can mmap or seek to the data region as needed.

use std::collections::HashMap;
use std::path::Path;

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::fs::File;
use tokio::io::{AsyncReadExt, BufReader};

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

#[derive(Error, Debug)]
pub enum GGUFError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Not a GGUF file (bad magic bytes)")]
    BadMagic,
    #[error("Unsupported GGUF version: {0}")]
    UnsupportedVersion(u32),
    #[error("Unknown value type: {0}")]
    UnknownValueType(u32),
    #[error("UTF-8 decode error: {0}")]
    Utf8(#[from] std::string::FromUtf8Error),
}

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

/// A scalar or array metadata value from the GGUF KV store.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum MetaValue {
    UInt8(u8),
    Int8(i8),
    UInt16(u16),
    Int16(i16),
    UInt32(u32),
    Int32(i32),
    Float32(f32),
    Bool(bool),
    Str(String),
    UInt64(u64),
    Int64(i64),
    Float64(f64),
    Array(Vec<MetaValue>),
}

/// Tensor descriptor — metadata only, no data bytes.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TensorInfo {
    pub name:        String,
    pub shape:       Vec<u64>,
    pub ggml_type:   u32,
    pub data_offset: u64,
}

/// Parsed GGUF file.
#[derive(Debug, Serialize, Deserialize)]
pub struct GGUFFile {
    pub version:  u32,
    pub metadata: HashMap<String, MetaValue>,
    pub tensors:  Vec<TensorInfo>,
}

// ---------------------------------------------------------------------------
// Async parser
// ---------------------------------------------------------------------------

const GGUF_MAGIC: u32 = 0x4647_4755; // "GGUF" in little-endian

struct Reader {
    inner: BufReader<File>,
}

impl Reader {
    async fn new(path: &Path) -> Result<Self, GGUFError> {
        Ok(Self { inner: BufReader::new(File::open(path).await?) })
    }

    async fn read_u8(&mut self) -> Result<u8, GGUFError> {
        Ok(self.inner.read_u8().await?)
    }
    async fn read_u16(&mut self) -> Result<u16, GGUFError> {
        Ok(self.inner.read_u16_le().await?)
    }
    async fn read_i16(&mut self) -> Result<i16, GGUFError> {
        Ok(self.inner.read_i16_le().await?)
    }
    async fn read_u32(&mut self) -> Result<u32, GGUFError> {
        Ok(self.inner.read_u32_le().await?)
    }
    async fn read_i32(&mut self) -> Result<i32, GGUFError> {
        Ok(self.inner.read_i32_le().await?)
    }
    async fn read_u64(&mut self) -> Result<u64, GGUFError> {
        Ok(self.inner.read_u64_le().await?)
    }
    async fn read_i64(&mut self) -> Result<i64, GGUFError> {
        Ok(self.inner.read_i64_le().await?)
    }
    async fn read_f32(&mut self) -> Result<f32, GGUFError> {
        Ok(f32::from_bits(self.inner.read_u32_le().await?))
    }
    async fn read_f64(&mut self) -> Result<f64, GGUFError> {
        Ok(f64::from_bits(self.inner.read_u64_le().await?))
    }

    async fn read_string(&mut self) -> Result<String, GGUFError> {
        let len = self.inner.read_u64_le().await? as usize;
        let mut buf = vec![0u8; len];
        self.inner.read_exact(&mut buf).await?;
        Ok(String::from_utf8(buf)?)
    }

    async fn read_value(&mut self, vtype: u32) -> Result<MetaValue, GGUFError> {
        match vtype {
            0  => Ok(MetaValue::UInt8(self.read_u8().await?)),
            1  => Ok(MetaValue::Int8(self.read_u8().await? as i8)),
            2  => Ok(MetaValue::UInt16(self.read_u16().await?)),
            3  => Ok(MetaValue::Int16(self.read_i16().await?)),
            4  => Ok(MetaValue::UInt32(self.read_u32().await?)),
            5  => Ok(MetaValue::Int32(self.read_i32().await?)),
            6  => Ok(MetaValue::Float32(self.read_f32().await?)),
            7  => Ok(MetaValue::Bool(self.read_u8().await? != 0)),
            8  => Ok(MetaValue::Str(self.read_string().await?)),
            9  => {
                let elem_type = self.read_u32().await?;
                let count     = self.read_u64().await?;
                let mut items = Vec::with_capacity(count.min(1024) as usize);
                for _ in 0..count {
                    items.push(self.read_value(elem_type).await?);
                }
                Ok(MetaValue::Array(items))
            }
            10 => Ok(MetaValue::UInt64(self.read_u64().await?)),
            11 => Ok(MetaValue::Int64(self.read_i64().await?)),
            12 => Ok(MetaValue::Float64(self.read_f64().await?)),
            other => Err(GGUFError::UnknownValueType(other)),
        }
    }
}

/// Parse a GGUF file asynchronously.
pub async fn parse(path: impl AsRef<Path>) -> Result<GGUFFile, GGUFError> {
    let path = path.as_ref();
    let mut r = Reader::new(path).await?;

    // Magic
    let magic = r.read_u32().await?;
    if magic != GGUF_MAGIC {
        return Err(GGUFError::BadMagic);
    }

    let version = r.read_u32().await?;
    if version < 1 || version > 3 {
        return Err(GGUFError::UnsupportedVersion(version));
    }

    let tensor_count: u64 = if version == 1 { r.read_u32().await? as u64 } else { r.read_u64().await? };
    let kv_count:     u64 = if version == 1 { r.read_u32().await? as u64 } else { r.read_u64().await? };

    // Metadata
    let mut metadata = HashMap::new();
    for _ in 0..kv_count {
        let key    = r.read_string().await?;
        let vtype  = r.read_u32().await?;
        let value  = r.read_value(vtype).await?;
        metadata.insert(key, value);
    }

    // Tensors
    let mut tensors = Vec::with_capacity(tensor_count as usize);
    for _ in 0..tensor_count {
        let name     = r.read_string().await?;
        let n_dims   = r.read_u32().await?;
        let mut dims = Vec::with_capacity(n_dims as usize);
        for _ in 0..n_dims {
            dims.push(r.read_u64().await?);
        }
        let ggml_type   = r.read_u32().await?;
        let data_offset = r.read_u64().await?;
        tensors.push(TensorInfo { name, shape: dims, ggml_type, data_offset });
    }

    Ok(GGUFFile { version, metadata, tensors })
}

// ---------------------------------------------------------------------------
// Binary entry point
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: gguf_parser <path.gguf> [--tensors]");
        std::process::exit(1);
    }
    let show_tensors = args.iter().any(|a| a == "--tensors");
    match parse(&args[1]).await {
        Ok(gguf) => {
            println!("GGUF version: {}", gguf.version);
            println!("Metadata keys: {}", gguf.metadata.len());
            println!("Tensors: {}", gguf.tensors.len());
            if show_tensors {
                println!("{}", serde_json::to_string_pretty(&gguf.tensors).unwrap());
            } else {
                println!("{}", serde_json::to_string_pretty(&gguf.metadata).unwrap());
            }
        }
        Err(e) => {
            eprintln!("Error: {e}");
            std::process::exit(1);
        }
    }
}
