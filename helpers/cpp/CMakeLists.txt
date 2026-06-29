cmake_minimum_required(VERSION 3.18)
project(symon_moe_helpers CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---------------------------------------------------------------------------
# Submodule paths (relative to repository root)
# ---------------------------------------------------------------------------
set(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../..")
set(LLAMA_CPP_DIR  "${REPO_ROOT}/converters/llm_engine")
set(SD_CPP_DIR     "${REPO_ROOT}/converters/diffusers_cpp")

# ---------------------------------------------------------------------------
# Option: use Eigen for tensor_ops (optional)
# ---------------------------------------------------------------------------
option(USE_EIGEN "Use Eigen for tensor arithmetic" OFF)

# ---------------------------------------------------------------------------
# gguf_reader — standalone GGUF parser library
# ---------------------------------------------------------------------------
add_library(gguf_reader STATIC
    gguf_reader.cpp
    gguf_reader.h
)
target_include_directories(gguf_reader PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# ---------------------------------------------------------------------------
# tensor_ops — basic tensor arithmetic library
# ---------------------------------------------------------------------------
add_library(tensor_ops STATIC
    tensor_ops.cpp
    tensor_ops.h
)
target_include_directories(tensor_ops PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

if(USE_EIGEN)
    find_package(Eigen3 REQUIRED)
    target_link_libraries(tensor_ops PUBLIC Eigen3::Eigen)
    target_compile_definitions(tensor_ops PRIVATE USE_EIGEN)
endif()

# ---------------------------------------------------------------------------
# llama_bridge — headless LLM inference CLI
# Requires llama.cpp to be built first:
#   cd ../../converters/llm_engine && cmake -B build && cmake --build build
# ---------------------------------------------------------------------------
set(LLAMA_LIB "${LLAMA_CPP_DIR}/build/src/libllama.so")
if(EXISTS "${LLAMA_CPP_DIR}/include/llama.h" AND EXISTS "${LLAMA_LIB}")
    add_executable(llama_bridge llama_bridge.cpp)
    target_include_directories(llama_bridge PRIVATE "${LLAMA_CPP_DIR}/include")
    target_link_libraries(llama_bridge PRIVATE "${LLAMA_LIB}" tensor_ops)
    message(STATUS "llama_bridge: enabled (llama.cpp found at ${LLAMA_CPP_DIR})")
else()
    message(WARNING
        "llama_bridge: SKIPPED — llama.cpp headers/library not found.\n"
        "  Build llama.cpp first: cd ${LLAMA_CPP_DIR} && cmake -B build && cmake --build build"
    )
endif()

# ---------------------------------------------------------------------------
# diffusion_bridge — headless text-to-image CLI
# Requires stable-diffusion.cpp to be built first:
#   cd ../../converters/diffusers_cpp && cmake -B build && cmake --build build
# ---------------------------------------------------------------------------
set(SD_LIB "${SD_CPP_DIR}/build/libstable-diffusion.so")
if(EXISTS "${SD_CPP_DIR}/stable-diffusion.h" AND EXISTS "${SD_LIB}")
    add_executable(diffusion_bridge diffusion_bridge.cpp)
    target_include_directories(diffusion_bridge PRIVATE "${SD_CPP_DIR}")
    target_link_libraries(diffusion_bridge PRIVATE "${SD_LIB}")
    message(STATUS "diffusion_bridge: enabled (stable-diffusion.cpp found at ${SD_CPP_DIR})")
else()
    message(WARNING
        "diffusion_bridge: SKIPPED — stable-diffusion.cpp not found.\n"
        "  Build it first: cd ${SD_CPP_DIR} && cmake -B build && cmake --build build"
    )
endif()

# ---------------------------------------------------------------------------
# Install targets
# ---------------------------------------------------------------------------
install(TARGETS gguf_reader tensor_ops
    ARCHIVE DESTINATION lib
    INCLUDES DESTINATION include
)
if(TARGET llama_bridge)
    install(TARGETS llama_bridge RUNTIME DESTINATION bin)
endif()
if(TARGET diffusion_bridge)
    install(TARGETS diffusion_bridge RUNTIME DESTINATION bin)
endif()
