import sys
from PySide6.QtCore import QThread, Signal
from ultralytics import YOLO

class AiWorker(QThread):
    finished_signal = Signal(str, list)
    error_signal = Signal(str)

    def __init__(self, model_path="yolov8n.pt", target_classes=None):
        super().__init__()
        self.model_path = model_path
        self.target_classes = target_classes # List of strings: ['car', 'bus']
        self.image_path = None
        self.model = None

    def update_config(self, model_path, target_classes_str):
        """动态更新配置"""
        if model_path and model_path != self.model_path:
            self.model_path = model_path
            self.model = None # 强制重新加载
        
        if target_classes_str:
            self.target_classes = [c.strip() for c in target_classes_str.split(',') if c.strip()]
        else:
            self.target_classes = None

    def set_image(self, image_path):
        self.image_path = image_path

    def load_model(self):
        if self.model is None:
            print(f"正在加载模型: {self.model_path}")
            self.model = YOLO(self.model_path) 

    def run(self):
        if not self.image_path: return

        try:
            self.load_model()
            results = self.model(self.image_path)
            
            detected_boxes = []
            for r in results:
                for box in r.boxes:
                    xywhn = box.xywhn[0].tolist() 
                    cls_id = int(box.cls[0])
                    
                    if hasattr(self.model, 'names'):
                        label = self.model.names[cls_id]
                    else:
                        label = str(cls_id)
                    
                    # 核心过滤逻辑：如果用户指定了类别，且当前物体不在列表里，就跳过
                    if self.target_classes and label not in self.target_classes:
                        continue

                    conf = float(box.conf[0])
                    detected_boxes.append({
                        "label": label,
                        "rect": xywhn,
                        "conf": conf
                    })
            
            self.finished_signal.emit(self.image_path, detected_boxes)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_signal.emit(str(e))