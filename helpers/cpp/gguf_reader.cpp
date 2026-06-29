// gguf_reader.cpp — Standalone GGUF binary parser implementation
//
// Parses GGUF v1, v2, and v3 files.  No external dependencies.
// Tensor DATA is not loaded; only offset information is recorded.

#include "gguf_reader.h"

#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>

namespace gguf {

static constexpr uint32_t GGUF_MAGIC = 0x46554747u; // "GGUF" LE

// ---- Low-level file reader helpers ---------------------------------------

struct FileReader {
    explicit FileReader(const std::string& path) {
        f.open(path, std::ios::binary);
        if (!f) throw std::runtime_error("Cannot open file: " + path);
    }

    template<typename T>
    T read() {
        T val{};
        f.read(reinterpret_cast<char*>(&val), sizeof(T));
        if (!f) throw std::runtime_error("Unexpected end of file");
        return val;
    }

    std::string read_string() {
        const uint64_t len = read<uint64_t>();
        std::string s(len, '\0');
        f.read(s.data(), static_cast<std::streamsize>(len));
        if (!f) throw std::runtime_error("Unexpected end of file reading string");
        return s;
    }

    std::streampos tell() { return f.tellg(); }
    void seek(std::streampos pos) { f.seekg(pos); }

    std::ifstream f;
};

// ---- Value parsing -------------------------------------------------------

static MetadataValue parse_value(FileReader& fr, ValueType vtype) {
    switch (vtype) {
        case ValueType::UINT8:   return fr.read<uint8_t>();
        case ValueType::INT8:    return fr.read<int8_t>();
        case ValueType::UINT16:  return fr.read<uint16_t>();
        case ValueType::INT16:   return fr.read<int16_t>();
        case ValueType::UINT32:  return fr.read<uint32_t>();
        case ValueType::INT32:   return fr.read<int32_t>();
        case ValueType::FLOAT32: return fr.read<float>();
        case ValueType::BOOL:    return static_cast<bool>(fr.read<uint8_t>());
        case ValueType::STRING:  return fr.read_string();
        case ValueType::UINT64:  return fr.read<uint64_t>();
        case ValueType::INT64:   return fr.read<int64_t>();
        case ValueType::FLOAT64: return fr.read<double>();
        case ValueType::ARRAY: {
            const auto elem_type = static_cast<ValueType>(fr.read<uint32_t>());
            const uint64_t count = fr.read<uint64_t>();
            // Simplification: store string repr of first N elements
            std::vector<std::string> elems;
            elems.reserve(count < 64 ? count : 64);
            for (uint64_t i = 0; i < count; ++i) {
                auto elem = parse_value(fr, elem_type);
                if (i < 64) {
                    if (std::holds_alternative<std::string>(elem))
                        elems.push_back(std::get<std::string>(elem));
                    else
                        elems.push_back("...");
                }
            }
            return elems;
        }
        default:
            throw std::runtime_error("Unknown GGUF value type: " +
                                     std::to_string(static_cast<uint32_t>(vtype)));
    }
}

// ---- GGUFReader::parse ---------------------------------------------------

void GGUFReader::parse() {
    FileReader fr(path_);

    const uint32_t magic = fr.read<uint32_t>();
    if (magic != GGUF_MAGIC)
        throw std::runtime_error("Not a GGUF file (bad magic): " + path_);

    version_ = fr.read<uint32_t>();
    if (version_ < 1 || version_ > 3)
        throw std::runtime_error("Unsupported GGUF version: " + std::to_string(version_));

    tensor_count_ = (version_ == 1) ? fr.read<uint32_t>() : fr.read<uint64_t>();
    kv_count_     = (version_ == 1) ? fr.read<uint32_t>() : fr.read<uint64_t>();

    // --- Metadata KV ---
    metadata_.reserve(kv_count_);
    for (uint64_t i = 0; i < kv_count_; ++i) {
        std::string key = fr.read_string();
        const auto vtype = static_cast<ValueType>(fr.read<uint32_t>());
        metadata_[key] = parse_value(fr, vtype);
    }

    // --- Tensor info ---
    tensors_.reserve(tensor_count_);
    for (uint64_t i = 0; i < tensor_count_; ++i) {
        TensorInfo ti;
        ti.name = fr.read_string();

        const uint32_t n_dims = fr.read<uint32_t>();
        ti.dims.resize(n_dims);
        for (uint32_t d = 0; d < n_dims; ++d)
            ti.dims[d] = fr.read<uint64_t>();

        ti.type        = fr.read<uint32_t>();
        ti.data_offset = fr.read<uint64_t>();

        tensors_.push_back(std::move(ti));
    }
}

// ---- GGUFReader public methods -------------------------------------------

GGUFReader::GGUFReader(const std::string& path) : path_(path) {
    parse();
}

GGUFReader::~GGUFReader() = default;

std::string GGUFReader::get_string(const std::string& key, const std::string& fallback) const {
    auto it = metadata_.find(key);
    if (it == metadata_.end()) return fallback;
    if (auto* v = std::get_if<std::string>(&it->second)) return *v;
    return fallback;
}

uint32_t GGUFReader::get_uint32(const std::string& key, uint32_t fallback) const {
    auto it = metadata_.find(key);
    if (it == metadata_.end()) return fallback;
    if (auto* v = std::get_if<uint32_t>(&it->second)) return *v;
    return fallback;
}

float GGUFReader::get_float32(const std::string& key, float fallback) const {
    auto it = metadata_.find(key);
    if (it == metadata_.end()) return fallback;
    if (auto* v = std::get_if<float>(&it->second)) return *v;
    return fallback;
}

} // namespace gguf
