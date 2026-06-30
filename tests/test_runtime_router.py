import unittest

from backend.app.model_runtime.runtime_router import route_runtime
from backend.app.model_runtime.schemas import DetectionMatch, RouteRequest


class RuntimeRouterTests(unittest.TestCase):
    def test_routes_chat_pipeline(self):
        request = RouteRequest(
            task="chat",
            inspection=DetectionMatch(
                detector="gguf",
                format="gguf",
                family="gguf",
                confidence=0.95,
                reasons=["Found GGUF artifact"],
                suggested_loader="workers.gguf.worker:GGUFWorker",
                suggested_converter="none",
                suggested_runtime="llama.cpp",
            ),
        )
        decision = route_runtime(request)
        self.assertEqual(decision.pipeline, "llm-inference")
        self.assertEqual(decision.worker, "gguf")

    def test_routes_deployment_with_device_profile(self):
        request = RouteRequest(
            task="deployment",
            target_device_profile="raspberry_pi_arm64",
            inspection=DetectionMatch(
                detector="onnx",
                format="onnx",
                family="onnx",
                confidence=0.95,
                reasons=["Found ONNX graph"],
                suggested_loader="workers.onnx.worker:ONNXWorker",
                suggested_converter="convert:onnx-optimize",
                suggested_runtime="onnxruntime",
            ),
        )
        decision = route_runtime(request)
        self.assertEqual(decision.device_profile, "raspberry_pi_arm64")
        self.assertEqual(decision.deployment_packaging, "embedded-package")

    def test_rejects_unknown_device_profile(self):
        request = RouteRequest(
            task="deployment",
            target_device_profile="unknown_profile",
            inspection=DetectionMatch(
                detector="onnx",
                format="onnx",
                family="onnx",
                confidence=0.95,
                reasons=["Found ONNX graph"],
                suggested_loader="workers.onnx.worker:ONNXWorker",
                suggested_converter="convert:onnx-optimize",
                suggested_runtime="onnxruntime",
            ),
        )
        with self.assertRaises(ValueError):
            route_runtime(request)


if __name__ == "__main__":
    unittest.main()
