import sys
from PySide6.QtCore import QThread, Signal
from ultralytics import YOLO

class AiWorker(QThread):
    # 信号：成功完成，返回 (图片路径, 识别结果列表)
    finished_signal = Signal(str, list)
    # 信号：报错
    error_signal = Signal(str)

    def __init__(self, model_path="yolov8n.pt"):
        super().__init__()
        self.model_path = model_path
        self.image_path = None
        self.model = None

    def set_image(self, image_path):
        self.image_path = image_path

    def load_model(self):
        """懒加载模型，只在第一次使用时加载"""
        if self.model is None:
            print("正在加载 YOLO 模型...")
            # 第一次运行会自动下载 yolov8n.pt (约6MB)
            self.model = YOLO(self.model_path) 

    def run(self):
        if not self.image_path:
            return

        try:
            self.load_model()
            
            # 开始推理
            results = self.model(self.image_path)
            
            # 解析结果
            detected_boxes = []
            for r in results:
                for box in r.boxes:
                    # 获取坐标 (x_center, y_center, width, height) 归一化格式 (0.0 ~ 1.0)
                    xywhn = box.xywhn[0].tolist() 
                    cls_id = int(box.cls[0])
                    label = self.model.names[cls_id]
                    conf = float(box.conf[0])
                    
                    detected_boxes.append({
                        "label": label,
                        "rect": xywhn, # [xc, yc, w, h]
                        "conf": conf
                    })
            
            # 发送结果回主界面
            self.finished_signal.emit(self.image_path, detected_boxes)

        except Exception as e:
            self.error_signal.emit(str(e))