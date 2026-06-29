#pragma once
// tensor_ops.h — Basic tensor arithmetic helpers
//
// Provides add, multiply (element-wise), dot product, and reshape for
// float32 tensors stored as contiguous 1-D arrays with explicit shape info.
// Optionally uses Eigen for optimised dot products when available.

#include <cstddef>
#include <stdexcept>
#include <vector>
#include <string>

namespace tensor {

// ---- Tensor descriptor ---------------------------------------------------

struct Tensor {
    std::vector<float>    data;
    std::vector<uint64_t> shape;   // dimensions, e.g. {3, 4} for a 3×4 matrix

    uint64_t n_elements() const {
        uint64_t n = 1;
        for (auto d : shape) n *= d;
        return n;
    }

    float& at(uint64_t idx)       { return data.at(idx); }
    float  at(uint64_t idx) const { return data.at(idx); }
};

// ---- Element-wise operations --------------------------------------------

// Element-wise addition: out[i] = a[i] + b[i]
Tensor add(const Tensor& a, const Tensor& b);

// Element-wise multiplication: out[i] = a[i] * b[i]
Tensor mul(const Tensor& a, const Tensor& b);

// Scalar scaling: out[i] = a[i] * scalar
Tensor scale(const Tensor& a, float scalar);

// ---- Matrix operations --------------------------------------------------

// Matrix multiply: C = A @ B  (A: M×K, B: K×N → C: M×N)
// Expects 2-D tensors with shapes [M, K] and [K, N].
Tensor matmul(const Tensor& A, const Tensor& B);

// Dot product: scalar result for 1-D tensors of equal length
float dot(const Tensor& a, const Tensor& b);

// ---- Shape operations ---------------------------------------------------

// Reshape without copying data (only validates total element count)
Tensor reshape(const Tensor& t, const std::vector<uint64_t>& new_shape);

// Transpose a 2-D tensor
Tensor transpose2d(const Tensor& t);

// ---- Factory helpers ----------------------------------------------------

// Create a zero-filled tensor
Tensor zeros(const std::vector<uint64_t>& shape);

// Create a tensor from a raw float array
Tensor from_data(const float* data, const std::vector<uint64_t>& shape);

} // namespace tensor
