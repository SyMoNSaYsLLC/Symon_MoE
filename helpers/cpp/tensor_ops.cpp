// tensor_ops.cpp — Basic tensor arithmetic implementation
//
// Plain C++ fallback (no external dependencies).  For production use,
// link against Eigen or BLAS by enabling USE_EIGEN in CMakeLists.txt.

#include "tensor_ops.h"

#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <cstring>

namespace tensor {

static void check_same_shape(const Tensor& a, const Tensor& b, const char* op) {
    if (a.shape != b.shape)
        throw std::invalid_argument(
            std::string(op) + ": shape mismatch"
        );
}

// ---- Element-wise -------------------------------------------------------

Tensor add(const Tensor& a, const Tensor& b) {
    check_same_shape(a, b, "add");
    Tensor out;
    out.shape = a.shape;
    out.data.resize(a.data.size());
    for (size_t i = 0; i < a.data.size(); ++i)
        out.data[i] = a.data[i] + b.data[i];
    return out;
}

Tensor mul(const Tensor& a, const Tensor& b) {
    check_same_shape(a, b, "mul");
    Tensor out;
    out.shape = a.shape;
    out.data.resize(a.data.size());
    for (size_t i = 0; i < a.data.size(); ++i)
        out.data[i] = a.data[i] * b.data[i];
    return out;
}

Tensor scale(const Tensor& a, float scalar) {
    Tensor out;
    out.shape = a.shape;
    out.data.resize(a.data.size());
    for (size_t i = 0; i < a.data.size(); ++i)
        out.data[i] = a.data[i] * scalar;
    return out;
}

// ---- Matrix operations --------------------------------------------------

Tensor matmul(const Tensor& A, const Tensor& B) {
    if (A.shape.size() != 2 || B.shape.size() != 2)
        throw std::invalid_argument("matmul: both tensors must be 2-D");
    const uint64_t M = A.shape[0];
    const uint64_t K = A.shape[1];
    const uint64_t N = B.shape[1];
    if (K != B.shape[0])
        throw std::invalid_argument("matmul: A columns != B rows");

    Tensor C = zeros({M, N});
    for (uint64_t m = 0; m < M; ++m)
        for (uint64_t n = 0; n < N; ++n) {
            float sum = 0.0f;
            for (uint64_t k = 0; k < K; ++k)
                sum += A.data[m * K + k] * B.data[k * N + n];
            C.data[m * N + n] = sum;
        }
    return C;
}

float dot(const Tensor& a, const Tensor& b) {
    if (a.shape.size() != 1 || b.shape.size() != 1)
        throw std::invalid_argument("dot: both tensors must be 1-D");
    if (a.data.size() != b.data.size())
        throw std::invalid_argument("dot: size mismatch");
    float result = 0.0f;
    for (size_t i = 0; i < a.data.size(); ++i)
        result += a.data[i] * b.data[i];
    return result;
}

// ---- Shape operations ---------------------------------------------------

Tensor reshape(const Tensor& t, const std::vector<uint64_t>& new_shape) {
    uint64_t new_total = 1;
    for (auto d : new_shape) new_total *= d;
    if (new_total != t.n_elements())
        throw std::invalid_argument("reshape: element count mismatch");
    Tensor out;
    out.shape = new_shape;
    out.data  = t.data;   // copy
    return out;
}

Tensor transpose2d(const Tensor& t) {
    if (t.shape.size() != 2)
        throw std::invalid_argument("transpose2d: tensor must be 2-D");
    const uint64_t M = t.shape[0];
    const uint64_t N = t.shape[1];
    Tensor out = zeros({N, M});
    for (uint64_t m = 0; m < M; ++m)
        for (uint64_t n = 0; n < N; ++n)
            out.data[n * M + m] = t.data[m * N + n];
    return out;
}

// ---- Factory helpers ----------------------------------------------------

Tensor zeros(const std::vector<uint64_t>& shape) {
    Tensor t;
    t.shape = shape;
    uint64_t n = 1;
    for (auto d : shape) n *= d;
    t.data.assign(n, 0.0f);
    return t;
}

Tensor from_data(const float* data, const std::vector<uint64_t>& shape) {
    Tensor t;
    t.shape = shape;
    uint64_t n = 1;
    for (auto d : shape) n *= d;
    t.data.assign(data, data + n);
    return t;
}

} // namespace tensor
