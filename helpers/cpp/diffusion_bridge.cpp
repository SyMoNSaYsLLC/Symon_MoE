// diffusion_bridge.cpp — Thin CLI wrapper around stable-diffusion.cpp for headless txt2img
//
// Provides a minimal command-line interface for text-to-image generation using
// the stable-diffusion.cpp library (converters/diffusers_cpp submodule).
//
// Usage:
//   diffusion_bridge --model model.gguf --prompt "a cat" --output out.png [options]

#include <cstdio>
#include <cstring>
#include <string>

// stable-diffusion.cpp public header (from submodule)
#include "stable-diffusion.h"

static void print_usage(const char* prog) {
    std::fprintf(stderr,
        "Usage: %s --model <path.gguf> --prompt <text> --output <out.png>"
        " [--negative <text>] [--width <N>] [--height <N>]"
        " [--steps <N>] [--cfg <float>] [--seed <N>]\n",
        prog);
}

struct BridgeParams {
    std::string model_path;
    std::string prompt;
    std::string negative_prompt;
    std::string output_path = "output.png";
    int    width  = 512;
    int    height = 512;
    int    steps  = 20;
    float  cfg    = 7.0f;
    int    seed   = 42;
    int    n_threads = -1;  // -1 = auto
};

static BridgeParams parse_args(int argc, char** argv) {
    BridgeParams p;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--model") == 0 && i + 1 < argc)
            p.model_path = argv[++i];
        else if (std::strcmp(argv[i], "--prompt") == 0 && i + 1 < argc)
            p.prompt = argv[++i];
        else if (std::strcmp(argv[i], "--negative") == 0 && i + 1 < argc)
            p.negative_prompt = argv[++i];
        else if (std::strcmp(argv[i], "--output") == 0 && i + 1 < argc)
            p.output_path = argv[++i];
        else if (std::strcmp(argv[i], "--width") == 0 && i + 1 < argc)
            p.width = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--height") == 0 && i + 1 < argc)
            p.height = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--steps") == 0 && i + 1 < argc)
            p.steps = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--cfg") == 0 && i + 1 < argc)
            p.cfg = static_cast<float>(std::atof(argv[++i]));
        else if (std::strcmp(argv[i], "--seed") == 0 && i + 1 < argc)
            p.seed = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--threads") == 0 && i + 1 < argc)
            p.n_threads = std::atoi(argv[++i]);
    }
    return p;
}

int main(int argc, char** argv) {
    if (argc < 2) { print_usage(argv[0]); return 1; }

    BridgeParams params = parse_args(argc, argv);
    if (params.model_path.empty() || params.prompt.empty()) {
        std::fprintf(stderr, "ERROR: --model and --prompt are required.\n");
        print_usage(argv[0]);
        return 1;
    }

    // Initialise stable-diffusion context
    sd_ctx_t* ctx = new_sd_ctx(
        /* model_path          */ params.model_path.c_str(),
        /* clip_l_path         */ "",
        /* clip_g_path         */ "",
        /* t5xxl_path          */ "",
        /* diffusion_model_path*/ "",
        /* vae_path            */ "",
        /* taesd_path          */ "",
        /* control_net_path    */ "",
        /* lora_model_dir      */ "",
        /* embed_dir           */ "",
        /* stacked_id_embed_dir*/ "",
        /* vae_decode_only     */ true,
        /* vae_tiling          */ false,
        /* free_params_immediately */ false,
        /* n_threads           */ params.n_threads,
        /* wtype               */ SD_TYPE_COUNT,   // use model default
        /* rng_type            */ STD_DEFAULT_RNG,
        /* schedule            */ DEFAULT,
        /* keep_clip_on_cpu    */ false,
        /* keep_control_net_cpu*/ false,
        /* keep_vae_on_cpu     */ false
    );

    if (!ctx) {
        std::fprintf(stderr, "ERROR: failed to create stable-diffusion context\n");
        return 1;
    }

    // Generate image
    sd_image_t* images = txt2img(
        ctx,
        params.prompt.c_str(),
        params.negative_prompt.c_str(),
        /* clip_skip       */ -1,
        params.cfg,
        /* guidance        */ 3.5f,
        params.width,
        params.height,
        EULER_A,
        params.steps,
        params.seed,
        /* batch_count     */ 1,
        /* control_image   */ nullptr,
        /* control_strength*/ 0.9f,
        /* style_ratio     */ 20.0f,
        /* normalize_input */ false,
        /* input_id_images_dir */ ""
    );

    if (!images || !images[0].data) {
        std::fprintf(stderr, "ERROR: image generation failed\n");
        free_sd_ctx(ctx);
        return 1;
    }

    // Write PNG output using stb_image_write (bundled with stable-diffusion.cpp)
    const int written = stbi_write_png(
        params.output_path.c_str(),
        images[0].width,
        images[0].height,
        images[0].channel,
        images[0].data,
        0
    );

    if (!written)
        std::fprintf(stderr, "WARNING: failed to write output PNG: %s\n", params.output_path.c_str());
    else
        std::fprintf(stdout, "Image written to: %s\n", params.output_path.c_str());

    free(images[0].data);
    delete[] images;
    free_sd_ctx(ctx);
    return written ? 0 : 1;
}
