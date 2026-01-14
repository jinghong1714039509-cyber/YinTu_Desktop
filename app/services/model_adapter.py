"""
AI 模型加载与推理适配层（插件化后端）

目标：
- 将 UI / Worker 与具体模型框架解耦
- 支持多种主流模型格式（至少覆盖：.pt/.onnx/.engine/.xml/.tflite/.mlmodel/.torchscript）
- 缺少可选依赖时给出明确、可操作的错误信息

当前实现：
- Ultralytics YOLO 后端（利用 Ultralytics 的多后端能力）
  - 只要 Ultralytics 支持该格式且依赖满足，即可推理
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Sequence, Set


class ModelLoadError(RuntimeError):
    """模型加载失败（用于向 UI/Worker 传递可读错误信息）"""


@dataclass(frozen=True)
class Detection:
    """统一检测结果结构：rect 使用 YOLO xywhn（归一化）"""
    label: str
    rect: Sequence[float]  # [x, y, w, h] normalized
    conf: float


class DetectionBackend:
    """检测模型后端抽象接口"""

    name: str = "base"
    supported_suffixes: Set[str] = set()

    def __init__(self, model_path: str):
        self.model_path = model_path

    def load(self) -> None:
        raise NotImplementedError

    def predict(self, image_path: str) -> List[Detection]:
        raise NotImplementedError

    def get_class_name(self, cls_id: int) -> str:
        return str(cls_id)


class UltralyticsYOLOBackend(DetectionBackend):
    """
    Ultralytics YOLO 后端

    说明：
    - Ultralytics 的 YOLO() 在不同格式下会自动选择后端
    - 部分格式需要额外依赖（如 onnxruntime/openvino 等）
    """

    name = "ultralytics-yolo"
    supported_suffixes = {
        ".pt", ".pth",
        ".onnx",
        ".engine",
        ".xml",
        ".tflite", ".pb",
        ".mlmodel",
        ".torchscript", ".ts",
    }

    def __init__(self, model_path: str):
        super().__init__(model_path)
        self._model = None

    def load(self) -> None:
        # 延迟导入：避免在没有安装 ultralytics 时直接崩溃（尽管 requirements 已包含）
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as e:
            raise ModelLoadError(
                "未检测到 ultralytics 依赖，无法加载模型。请执行：pip install ultralytics"
            ) from e

        # OpenVINO 格式通常需要同目录 .bin
        if self.model_path.lower().endswith(".xml"):
            bin_path = os.path.splitext(self.model_path)[0] + ".bin"
            if not os.path.exists(bin_path):
                raise ModelLoadError(
                    f"检测到 OpenVINO 模型（.xml），但未找到配套的 .bin 文件：{bin_path}\n"
                    "请确认 .xml 与 .bin 位于同一目录且文件名一致。"
                )

        try:
            self._model = YOLO(self.model_path)
        except Exception as e:
            # 典型：onnxruntime 未安装 / OpenVINO 未安装 / TRT 运行时缺失等
            msg = str(e)
            hint = []

            low = msg.lower()
            if "onnx" in low and ("runtime" in low or "onnxruntime" in low):
                hint.append("可能缺少 onnxruntime，请执行：pip install onnxruntime 或 onnxruntime-gpu")
            if "openvino" in low:
                hint.append("可能缺少 openvino，请执行：pip install openvino")
            if "tensorrt" in low or "trt" in low or "engine" in low:
                hint.append("TensorRT 后端需要本机已安装 TensorRT 与匹配的 CUDA/cuDNN 环境。")
            if "coreml" in low or "mlmodel" in low:
                hint.append("CoreML 一般仅在 macOS 环境可用。")
            if "tflite" in low or "tensorflow" in low:
                hint.append("TFLite/TF 后端可能需要 tensorflow，请执行：pip install tensorflow（或对应平台版本）")

            if hint:
                msg = msg + "\n\n可选依赖提示：\n- " + "\n- ".join(hint)

            raise ModelLoadError(f"模型加载失败：{msg}") from e

    def predict(self, image_path: str) -> List[Detection]:
        if self._model is None:
            self.load()

        try:
            results = self._model(image_path)
        except Exception as e:
            raise ModelLoadError(f"模型推理失败：{e}") from e

        detections: List[Detection] = []
        for r in results:
            if not hasattr(r, "boxes") or r.boxes is None:
                continue
            for box in r.boxes:
                xywhn = box.xywhn[0].tolist()
                cls_id = int(box.cls[0])

                label = self.get_class_name(cls_id)
                if hasattr(self._model, "names") and isinstance(self._model.names, (dict, list)):
                    try:
                        label = self._model.names[cls_id]  # type: ignore[index]
                    except Exception:
                        pass

                conf = float(box.conf[0])
                detections.append(Detection(label=label, rect=xywhn, conf=conf))

        return detections


class ModelRegistry:
    """根据模型文件自动选择后端（可扩展）"""

    _backends = [UltralyticsYOLOBackend]

    @classmethod
    def register(cls, backend_cls):
        cls._backends.insert(0, backend_cls)

    @classmethod
    def load_backend(cls, model_path: str) -> DetectionBackend:
        model_path = model_path or ""
        model_path = os.path.abspath(model_path)

        if not os.path.exists(model_path):
            raise ModelLoadError(f"模型文件不存在：{model_path}")

        # 目录型模型（如 TF SavedModel）暂时交给 ultralytics 尝试（如果不支持，会给出明确错误）
        suffix = "" if os.path.isdir(model_path) else os.path.splitext(model_path)[1].lower()

        for backend_cls in cls._backends:
            if os.path.isdir(model_path) or (suffix in backend_cls.supported_suffixes):
                backend = backend_cls(model_path)
                backend.load()
                return backend

        raise ModelLoadError(
            f"不支持的模型格式：{suffix or '目录'}。\n"
            "当前支持：.pt/.pth/.onnx/.engine/.xml/.tflite/.pb/.mlmodel/.torchscript/.ts"
        )
