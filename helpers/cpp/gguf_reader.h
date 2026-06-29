#pragma once
// gguf_reader.h — Standalone GGUF binary parser (no llama.cpp dependency)
//
// Provides a minimal, dependency-free parser for the GGUF v1/v2/v3 binary
// format.  Only the metadata KV section and the tensor info table are parsed;
// tensor data is mapped by offset but not loaded into memory.
//
// Usage:
//   GGUFReader reader("path/to/model.gguf");
//   auto meta  = reader.metadata();
//   auto tensors = reader.tensors();

#include <cstdint>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>
#include <stdexcept>

namespace gguf {

// ---- Value types ---------------------------------------------------------

enum class ValueType : uint32_t {
    UINT8   = 0,
    INT8    = 1,
    UINT16  = 2,
    INT16   = 3,
    UINT32  = 4,
    INT32   = 5,
    FLOAT32 = 6,
    BOOL    = 7,
    STRING  = 8,
    ARRAY   = 9,
    UINT64  = 10,
    INT64   = 11,
    FLOAT64 = 12,
};

// Scalar metadata value (arrays stored as vector<MetadataValue>)
using MetadataValue = std::variant<
    uint8_t, int8_t, uint16_t, int16_t,
    uint32_t, int32_t, float, bool,
    std::string, uint64_t, int64_t, double,
    std::vector<std::string>   // simplified array representation
>;

// ---- Tensor info ---------------------------------------------------------

struct TensorInfo {
    std::string name;
    std::vector<uint64_t> dims;   // shape (n_dims elements)
    uint32_t type;                // GGMLType enum value
    uint64_t data_offset;         // byte offset from tensor data region start
};

// ---- Reader --------------------------------------------------------------

class GGUFReader {
public:
    explicit GGUFReader(const std::string& path);
    ~GGUFReader();

    uint32_t version()          const { return version_; }
    uint64_t tensor_count()     const { return tensor_count_; }
    uint64_t metadata_kv_count() const { return kv_count_; }

    const std::unordered_map<std::string, MetadataValue>& metadata() const { return metadata_; }
    const std::vector<TensorInfo>& tensors() const { return tensors_; }

    // Convenience accessors
    std::string get_string(const std::string& key, const std::string& fallback = "") const;
    uint32_t    get_uint32(const std::string& key, uint32_t fallback = 0) const;
    float       get_float32(const std::string& key, float fallback = 0.0f) const;

private:
    void parse();

    std::string  path_;
    uint32_t     version_      = 0;
    uint64_t     tensor_count_ = 0;
    uint64_t     kv_count_     = 0;
    std::unordered_map<std::string, MetadataValue> metadata_;
    std::vector<TensorInfo> tensors_;
};

} // namespace gguf
