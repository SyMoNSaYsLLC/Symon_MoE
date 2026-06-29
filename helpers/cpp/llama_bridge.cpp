// llama_bridge.cpp — Thin CLI wrapper around llama_context for headless inference
//
// Provides a minimal command-line interface for text generation using a
// llama.cpp-based model.  Link against the llama.cpp shared library from
// the converters/llm_engine submodule.
//
// Usage:
//   llama_bridge --model model.gguf --prompt "Hello world" [--n-predict 128]

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

// llama.cpp public header (from submodule)
#include "llama.h"

static void print_usage(const char* prog) {
    std::fprintf(stderr,
        "Usage: %s --model <path.gguf> --prompt <text>"
        " [--n-predict <N>] [--n-ctx <N>] [--temp <float>] [--seed <N>]\n",
        prog);
}

struct BridgeParams {
    std::string model_path;
    std::string prompt;
    int         n_predict = 256;
    int         n_ctx     = 2048;
    float       temp      = 0.8f;
    uint32_t    seed      = 42;
};

static BridgeParams parse_args(int argc, char** argv) {
    BridgeParams p;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--model") == 0 && i + 1 < argc)
            p.model_path = argv[++i];
        else if (std::strcmp(argv[i], "--prompt") == 0 && i + 1 < argc)
            p.prompt = argv[++i];
        else if (std::strcmp(argv[i], "--n-predict") == 0 && i + 1 < argc)
            p.n_predict = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--n-ctx") == 0 && i + 1 < argc)
            p.n_ctx = std::atoi(argv[++i]);
        else if (std::strcmp(argv[i], "--temp") == 0 && i + 1 < argc)
            p.temp = static_cast<float>(std::atof(argv[++i]));
        else if (std::strcmp(argv[i], "--seed") == 0 && i + 1 < argc)
            p.seed = static_cast<uint32_t>(std::atoi(argv[++i]));
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

    // Initialise llama.cpp backend
    llama_backend_init();

    // Load model
    llama_model_params mparams = llama_model_default_params();
    llama_model* model = llama_load_model_from_file(params.model_path.c_str(), mparams);
    if (!model) {
        std::fprintf(stderr, "ERROR: failed to load model: %s\n", params.model_path.c_str());
        llama_backend_free();
        return 1;
    }

    // Create context
    llama_context_params cparams = llama_context_default_params();
    cparams.n_ctx  = static_cast<uint32_t>(params.n_ctx);
    cparams.seed   = params.seed;
    llama_context* ctx = llama_new_context_with_model(model, cparams);
    if (!ctx) {
        std::fprintf(stderr, "ERROR: failed to create context\n");
        llama_free_model(model);
        llama_backend_free();
        return 1;
    }

    // Tokenise prompt
    const int n_vocab = llama_n_vocab(model);
    std::vector<llama_token> tokens(params.prompt.size() + 4);
    const int n_tokens = llama_tokenize(
        model,
        params.prompt.c_str(),
        static_cast<int32_t>(params.prompt.size()),
        tokens.data(),
        static_cast<int32_t>(tokens.size()),
        /* add_bos */ true,
        /* special */ false
    );
    if (n_tokens < 0) {
        std::fprintf(stderr, "ERROR: tokenisation failed\n");
        llama_free(ctx);
        llama_free_model(model);
        llama_backend_free();
        return 1;
    }
    tokens.resize(n_tokens);

    // Evaluate prompt
    llama_batch batch = llama_batch_get_one(tokens.data(), n_tokens, 0, 0);
    if (llama_decode(ctx, batch) != 0) {
        std::fprintf(stderr, "ERROR: initial decode failed\n");
        llama_free(ctx);
        llama_free_model(model);
        llama_backend_free();
        return 1;
    }

    // Sample and generate
    llama_sampler* smpl = llama_sampler_chain_init(llama_sampler_chain_default_params());
    llama_sampler_chain_add(smpl, llama_sampler_init_temp(params.temp));
    llama_sampler_chain_add(smpl, llama_sampler_init_dist(params.seed));

    int n_cur = n_tokens;
    for (int i = 0; i < params.n_predict; ++i) {
        const llama_token tok = llama_sampler_sample(smpl, ctx, -1);
        if (llama_token_is_eog(model, tok)) break;

        char buf[128] = {};
        const int n = llama_token_to_piece(model, tok, buf, sizeof(buf) - 1, 0, false);
        if (n > 0) {
            buf[n] = '\0';
            std::fputs(buf, stdout);
            std::fflush(stdout);
        }

        llama_batch next = llama_batch_get_one(&tok, 1, n_cur++, 0);
        if (llama_decode(ctx, next) != 0) break;
    }
    std::fputc('\n', stdout);

    llama_sampler_free(smpl);
    llama_free(ctx);
    llama_free_model(model);
    llama_backend_free();
    return 0;
}
