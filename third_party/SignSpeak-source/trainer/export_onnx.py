"""Export backend/models/asl.pt (ASLLSTM) to ONNX for on-device inference.

Usage:
    python export_onnx.py

Writes web/public/models/asl.onnx and verifies output parity against PyTorch.
"""
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from inference.model import ASLLSTM  # noqa: E402

MODEL_IN = ROOT / "backend" / "models" / "asl.pt"
MODEL_OUT = ROOT / "web" / "public" / "models" / "asl.onnx"
SEQ_LEN = 30
FEATURES = 63


def main():
    model = ASLLSTM()
    state = torch.load(MODEL_IN, map_location="cpu")
    model.load_state_dict(state)
    model.eval()

    dummy = torch.randn(1, SEQ_LEN, FEATURES)
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy,
        str(MODEL_OUT),
        input_names=["input"],
        output_names=["logits"],
        opset_version=17,
        dynamo=False,  # legacy exporter handles nn.LSTM cleanly
    )

    # ---- parity check ----
    import onnxruntime as ort

    sess = ort.InferenceSession(str(MODEL_OUT), providers=["CPUExecutionProvider"])
    rng = np.random.default_rng(42)
    max_diff = 0.0
    for _ in range(5):
        x = rng.standard_normal((1, SEQ_LEN, FEATURES)).astype(np.float32)
        with torch.no_grad():
            ref = model(torch.from_numpy(x)).numpy()
        out = sess.run(None, {"input": x})[0]
        max_diff = max(max_diff, float(np.abs(ref - out).max()))

    print(f"Exported {MODEL_OUT} ({MODEL_OUT.stat().st_size} bytes)")
    print(f"Max logit diff vs PyTorch over 5 random inputs: {max_diff:.2e}")
    assert max_diff < 1e-4, "Parity check failed"
    print("Parity check PASSED")


if __name__ == "__main__":
    main()
