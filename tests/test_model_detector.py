import unittest

from backend.app.model_runtime.detector import inspect_model


class ModelDetectorTests(unittest.TestCase):
    def test_detects_gguf(self):
        result = inspect_model("/virtual/model.gguf", ["model.gguf"])
        self.assertEqual(result.selected.format, "gguf")
        self.assertEqual(result.selected.suggested_runtime, "llama.cpp")

    def test_detects_transformers(self):
        result = inspect_model("/virtual/model", ["config.json", "tokenizer.json", "model.safetensors"])
        self.assertEqual(result.selected.format, "transformers")
        self.assertIn("workers.transformers.worker:TransformersWorker", result.selected.suggested_loader)


if __name__ == "__main__":
    unittest.main()
