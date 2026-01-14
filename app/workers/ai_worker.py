from PySide6.QtCore import QThread, Signal

from app.services.model_adapter import ModelRegistry, ModelLoadError


class AiWorker(QThread):
    """
    AI 推理线程

    - 通过 ModelRegistry 实现多模型格式支持（.pt/.onnx/.engine/.xml/.tflite/...）
    - 推理输出统一为：[{label, rect(xywhn), conf}, ...]
    """

    finished_signal = Signal(str, list)
    error_signal = Signal(str)

    def __init__(self, model_path: str = "yolov8n.pt", target_classes=None):
        super().__init__()
        self.model_path = model_path
        self.target_classes = target_classes  # List[str] or None
        self.image_path = None

        # backend 是已加载的推理后端（支持不同格式/框架）
        self.backend = None

    def update_config(self, model_path, target_classes_str):
        """动态更新配置"""
        if model_path and model_path != self.model_path:
            self.model_path = model_path
            self.backend = None  # 强制重新加载

        if target_classes_str:
            self.target_classes = [c.strip() for c in target_classes_str.split(',') if c.strip()]
        else:
            self.target_classes = None

    def set_image(self, image_path):
        self.image_path = image_path

    def load_model(self):
        """按需加载模型（支持多格式）"""
        if self.backend is None:
            self.backend = ModelRegistry.load_backend(self.model_path)

    def run(self):
        if not self.image_path:
            return

        try:
            self.load_model()

            detections = self.backend.predict(self.image_path)

            detected_boxes = []
            for det in detections:
                label = det.label

                # 核心过滤逻辑：如果用户指定了类别，且当前物体不在列表里，就跳过
                if self.target_classes and label not in self.target_classes:
                    continue

                detected_boxes.append({
                    "label": label,
                    "rect": list(det.rect),
                    "conf": float(det.conf)
                })

            self.finished_signal.emit(self.image_path, detected_boxes)

        except ModelLoadError as e:
            self.error_signal.emit(str(e))
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_signal.emit(str(e))
