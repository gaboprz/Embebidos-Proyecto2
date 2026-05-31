"""
Inferencia híbrida: ONNX Runtime + TensorRT (corregido para Jetson)
"""

import sys
import json
import numpy as np
from PIL import Image
from pathlib import Path

import onnxruntime as ort

# =====================
# CONFIG
# =====================
CLASS_NAMES = ['Black Sigatoka', 'Healthy', 'Panama', 'Yellow Sigatoka']

MODEL_DIR = Path("./weights")
ONNX_PATH = MODEL_DIR / "best_model.onnx"
TRT_PATH = MODEL_DIR / "best_model_fp16.trt"


# =====================
# PREPROCESS
# =====================
def preprocess_image(image_path, size=224):
    img = Image.open(image_path).convert('RGB')
    img = img.resize((size, size), Image.BILINEAR)

    img_array = np.array(img).astype(np.float32) / 255.0

    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    img_array = (img_array - mean) / std
    img_array = np.transpose(img_array, (2, 0, 1))
    img_array = np.expand_dims(img_array, axis=0)

    return img_array.astype(np.float32)


# =====================
# ONNX (GLOBAL SESSION)
# =====================
onnx_session = ort.InferenceSession(str(ONNX_PATH))
onnx_input_name = onnx_session.get_inputs()[0].name


def infer_onnx(image_path):
    img_array = preprocess_image(image_path)
    outputs = onnx_session.run(None, {onnx_input_name: img_array})
    return outputs[0][0]


# =====================
# TENSORRT (SAFE LOAD)
# =====================
def load_tensorrt_engine():
    import tensorrt as trt

    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
    runtime = trt.Runtime(TRT_LOGGER)

    with open(str(TRT_PATH), "rb") as f:
        engine = runtime.deserialize_cuda_engine(f.read())

    context = engine.create_execution_context()
    return engine, context


def infer_tensorrt(image_path):
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit

    engine, context = load_tensorrt_engine()

    # =====================
    # INPUT / OUTPUT SETUP (MODERNO)
    # =====================
    input_name = None
    output_name = None

    bindings = []
    host_mem = {}
    device_mem = {}

    for i in range(engine.num_io_tensors):
        name = engine.get_tensor_name(i)
        shape = engine.get_tensor_shape(name)
        dtype = trt.nptype(engine.get_tensor_dtype(name))

        size = trt.volume(shape)

        h_mem = cuda.pagelocked_empty(size, dtype)
        d_mem = cuda.mem_alloc(h_mem.nbytes)

        bindings.append(int(d_mem))
        host_mem[name] = h_mem
        device_mem[name] = d_mem

        if engine.get_tensor_mode(name).name == "INPUT":
            input_name = name
        else:
            output_name = name

    # =====================
    # PREPROCESS
    # =====================
    input_data = preprocess_image(image_path)

    np.copyto(host_mem[input_name], input_data.ravel())

    stream = cuda.Stream()

    # H2D
    cuda.memcpy_htod_async(device_mem[input_name], host_mem[input_name], stream)

    # EXEC
    context.execute_async_v2(bindings=bindings, stream_handle=stream.handle)

    # D2H
    cuda.memcpy_dtoh_async(host_mem[output_name], device_mem[output_name], stream)

    stream.synchronize()

    output = np.array(host_mem[output_name])
    return output


# =====================
# PREDICT
# =====================
def predict(image_path):
    use_tensorrt = TRT_PATH.exists()

    try:
        if use_tensorrt:
            logits = infer_tensorrt(image_path)
            engine_used = "tensorrt"
        else:
            logits = infer_onnx(image_path)
            engine_used = "onnx"

        logits = np.array(logits)

        # Softmax estable
        exp_logits = np.exp(logits - np.max(logits))
        probabilities = exp_logits / np.sum(exp_logits)

        pred_idx = int(np.argmax(probabilities))
        confidence = float(probabilities[pred_idx] * 100)

        return {
            "success": True,
            "prediction": {
                "disease": CLASS_NAMES[pred_idx],
                "confidence": confidence,
                "is_certain": confidence >= 75
            },
            "probabilities": {
                CLASS_NAMES[i]: float(probabilities[i] * 100)
                for i in range(len(CLASS_NAMES))
            },
            "engine": engine_used
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =====================
# MAIN
# =====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "No image path provided"
        }))
        sys.exit(1)

    result = predict(sys.argv[1])
    print(json.dumps(result, indent=2))