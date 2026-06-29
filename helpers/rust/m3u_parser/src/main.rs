//! m3u_parser — M3U/M3U8 playlist parser and channel fetcher for IPTV
//!
//! Parses the extended M3U format (`#EXTM3U` / `#EXTINF` headers) and fetches
//! remote playlists via HTTP(S).  Returns a structured list of channels that
//! the IPTV frontend app can display.

use std::collections::HashMap;

use reqwest::Client;
use serde::{Deserialize, Serialize};
use thiserror::Error;

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

#[derive(Error, Debug)]
pub enum M3UError {
    #[error("HTTP error fetching playlist: {0}")]
    Http(#[from] reqwest::Error),
    #[error("Invalid M3U format: {0}")]
    Format(String),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

// ---------------------------------------------------------------------------
// Data types
// ---------------------------------------------------------------------------

/// A single IPTV channel parsed from an M3U playlist.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Channel {
    /// Channel display name.
    pub name:      String,
    /// Stream URL.
    pub url:       String,
    /// Group/category name (from `group-title` attribute).
    pub group:     Option<String>,
    /// Logo URL (from `tvg-logo` attribute).
    pub logo:      Option<String>,
    /// EPG channel ID (from `tvg-id` attribute).
    pub tvg_id:    Option<String>,
    /// Any additional #EXTINF attributes not explicitly recognised above.
    pub extra:     HashMap<String, String>,
}

/// A parsed M3U playlist.
#[derive(Debug, Serialize, Deserialize)]
pub struct Playlist {
    pub channels: Vec<Channel>,
    pub source:   String,
}

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

/// Parse an M3U/M3U8 string into a `Playlist`.
pub fn parse_str(content: &str, source: impl Into<String>) -> Result<Playlist, M3UError> {
    let mut lines = content.lines().peekable();

    // The first non-empty line should be #EXTM3U (or we accept it anyway)
    let first = lines.next().unwrap_or("").trim();
    if !first.starts_with("#EXTM3U") && !first.is_empty() {
        return Err(M3UError::Format("Missing #EXTM3U header".into()));
    }

    let mut channels = Vec::new();
    let mut pending_extinf: Option<String> = None;

    for raw_line in lines {
        let line = raw_line.trim();
        if line.is_empty() || line.starts_with("#EXTM3U") {
            continue;
        }
        if line.starts_with("#EXTINF:") {
            pending_extinf = Some(line[8..].to_owned());
            continue;
        }
        if line.starts_with('#') {
            continue; // Other directives — ignore
        }
        // This line is the stream URL
        let url = line.to_owned();
        let channel = if let Some(extinf) = pending_extinf.take() {
            parse_extinf(&extinf, url)
        } else {
            Channel {
                name:   url.clone(),
                url,
                group:  None,
                logo:   None,
                tvg_id: None,
                extra:  HashMap::new(),
            }
        };
        channels.push(channel);
    }

    Ok(Playlist { channels, source: source.into() })
}

/// Parse a single `#EXTINF` value (the part after `#EXTINF:`).
///
/// Format: `<duration> [key="value" ...],<channel name>`
fn parse_extinf(extinf: &str, url: String) -> Channel {
    // Split on the last comma to get attributes and name
    let (attrs_part, name) = if let Some(comma) = extinf.rfind(',') {
        (&extinf[..comma], extinf[comma + 1..].trim().to_owned())
    } else {
        (extinf, extinf.to_owned())
    };

    let mut extra: HashMap<String, String> = HashMap::new();
    let mut group:  Option<String> = None;
    let mut logo:   Option<String> = None;
    let mut tvg_id: Option<String> = None;

    // Parse key="value" pairs after the duration field
    let mut remaining = attrs_part;
    // Skip the duration token
    if let Some(idx) = remaining.find(|c: char| c.is_whitespace()) {
        remaining = &remaining[idx..];
    } else {
        remaining = "";
    }

    // Simple key="value" extractor (no nom needed for this subset)
    let mut chars = remaining.chars().peekable();
    while chars.peek().is_some() {
        // Skip whitespace
        while chars.peek().map_or(false, |c| c.is_whitespace()) {
            chars.next();
        }
        // Read key
        let key: String = chars.by_ref().take_while(|&c| c != '=').collect();
        let key = key.trim().to_owned();
        if key.is_empty() {
            break;
        }
        // Expect opening quote
        if chars.next() != Some('"') {
            break;
        }
        // Read value up to closing quote
        let value: String = chars.by_ref().take_while(|&c| c != '"').collect();

        match key.as_str() {
            "group-title" => group  = Some(value.clone()),
            "tvg-logo"    => logo   = Some(value.clone()),
            "tvg-id"      => tvg_id = Some(value.clone()),
            _             => { extra.insert(key.clone(), value.clone()); }
        }
    }

    Channel { name, url, group, logo, tvg_id, extra }
}

// ---------------------------------------------------------------------------
// HTTP fetcher
// ---------------------------------------------------------------------------

/// Fetch and parse a remote M3U playlist.
pub async fn fetch_playlist(url: &str) -> Result<Playlist, M3UError> {
    let client = Client::builder()
        .user_agent("Symon_MoE/1.0 m3u_parser")
        .build()?;
    let content = client.get(url).send().await?.text().await?;
    parse_str(&content, url)
}

/// Fetch and return only channels from a specific group.
pub async fn fetch_channels_by_group(
    url: &str,
    group: &str,
) -> Result<Vec<Channel>, M3UError> {
    let playlist = fetch_playlist(url).await?;
    Ok(playlist
        .channels
        .into_iter()
        .filter(|c| c.group.as_deref().unwrap_or("").eq_ignore_ascii_case(group))
        .collect())
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: m3u_parser <url_or_file> [--group <name>]");
        std::process::exit(1);
    }

    let source = &args[1];
    let group_filter = args.windows(2).find(|w| w[0] == "--group").map(|w| w[1].clone());

    let playlist = if source.starts_with("http://") || source.starts_with("https://") {
        fetch_playlist(source).await
    } else {
        let content = tokio::fs::read_to_string(source).await.map_err(M3UError::Io)?;
        parse_str(&content, source.as_str())
    };

    match playlist {
        Ok(mut p) => {
            if let Some(g) = &group_filter {
                p.channels.retain(|c| c.group.as_deref().unwrap_or("").eq_ignore_ascii_case(g));
            }
            println!("{}", serde_json::to_string_pretty(&p.channels).unwrap());
        }
        Err(e) => {
            eprintln!("Error: {e}");
            std::process::exit(1);
        }
    }
}
