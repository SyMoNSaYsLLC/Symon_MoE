# Symon_MoE

To build your symon
_
moe repository for model conversion, you need two distinct,
non-interchangeable conversion engines. You cannot "merge" them; you must bridge them by
invoking their respective tools.
Here is your procedure to establish the conversion foundation for your repo.
1. Structure the symon
_
moe Repo
Use Git submodules. This keeps your repo clean and allows you to git pull updates from the
upstream developers (the "base model" repo maintainers) while keeping your own conversion
scripts in a separate orchestration/ folder.
mkdir symon
moe && cd symon
moe
_
_
git init
mkdir orchestration converters
# Add the official engines as submodules
git submodule add https://github.com/ggml-org/llama.cpp.git
converters/llm
engine
_
git submodule add https://github.com/city96/ComfyUI-GGUF.git
converters/diff
engine
_
2. Individual Architecture Converters
To fulfill your goal of converting "all architectures individually,
" here is how you call them from
your manager.
For Text/VLM (Qwen, Llama, Mistral, Gemma, etc.)
The llama.cpp script is your universal converter for these.
●
The Command:
python3 converters/llm
engine/convert-hf-to-gguf.py <model
_
_
--outfile <name>.gguf --outtype q8
0
dir>
_
●
Architectures Supported: This script uses a registry (inside the convert-hf-to-gguf.py
file) that maps architecture names (e.g., Qwen2ForCausalLM) to specific loading classes.
It automatically handles the conversion for any architecture supported by llama.cpp.
For Diffusion/Flux (Flux, SD3, SDXL)
These use a separate logic because they are Diffusion Transformers, not LLMs.
●
The Command:
python3 converters/diff
engine/tools/convert.py --src
_
<model
file>.safetensors --dst <name>.gguf
_
●
Supported Architectures: This script specifically targets the flux and sd3 architectures
defined in its own ModelTemplate registry.
3. The "Glue" Logic (orchestration/convert.py)
Create this script in your orchestration/ folder. It acts as the "smart" layer that detects the
architecture and calls the correct engine.
import subprocess
import json
import os
def convert(model
path):
_
# 1. Inspect config.json to identify the architecture
with open(os.path.join(model
path,
"config.json"),
_
config = json.load(f)
"r") as f:
arch = config.get("architectures"
, [None])[0]
# 2. Dispatch to the correct engine
if "Flux" in arch or "SD3" in arch:
# Call the Diffusion Converter
subprocess.run(["python3"
,
"converters/diff
engine/tools/convert.py"
_
"
--dst"
,
"flux.gguf"])
else:
"
,
--src"
, model
path,
_
# Default to LLM converter for Qwen, Llama, etc.
subprocess.run(["python3"
,
"converters/llm
engine/convert-hf-to-gguf.py"
, model
path,
_
_
"
--outfile"
,
"model.gguf"])
Summary of what you have now:
1. Legal Safety: By using submodules, the LICENSE files from llama.cpp and
ComfyUI-GGUF remain in their respective directories, keeping you compliant.
2. Base Model Starting Point: You can point your orchestration/convert.py at any raw
Hugging Face directory (the "base model").
3. Individual Architecture Control: You now have the exact paths to the conversion scripts
that the maintainers of these repos use themselves

## Interface modules

Add interface-focused submodules alongside the conversion engines:

```bash
git submodule add https://github.com/anomalyco/opencode.git interfaces/opencode_cli
git submodule add https://github.com/ggml-org/llama.cpp.git interfaces/llama_cpp_server
```