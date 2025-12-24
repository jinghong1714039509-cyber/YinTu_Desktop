# YinTu_Desktop

# YinTu Desktop (音图智能标注系统 - 桌面版)

YinTu Desktop 是一个基于 **PySide6** 和 **YOLO** 构建的本地化 AI 智能数据标注平台。它旨在为计算机视觉任务（如目标检测）提供高效、流畅的数据集管理与标注体验。支持图片直接导入及视频自动抽帧处理。

## 🚀 核心功能 (Current Features)

### 1. 项目与数据管理
- **本地化离线运行**：无需上传数据，直接管理本地文件夹。
- **智能导入**：
  - 支持直接打开包含图片 (`.jpg`, `.png`) 的文件夹。
  - **视频自动处理**：检测到视频文件 (`.mp4`, `.avi`) 时，后台线程自动进行抽帧处理，不阻塞 UI。
- **SQLite 数据库管理**：使用 Peewee ORM 自动建立项目索引，记录文件路径与标注状态。

### 2. 专业级标注工作台 (Label Workbench)
- **高性能画布**：
  - **平滑缩放**：支持鼠标滚轮以鼠标为中心无限放大/缩小，画质清晰无锯齿。
  - **自由拖拽**：按住鼠标左键或中键即可平移画布。
  - **自适应视图**：图片加载或窗口调整时，自动适配最佳显示比例。
- **交互式绘图**：
  - **浏览模式 (View)**：纯净查看，防误触。
  - **标注模式 (Draw)**：提供矩形框绘制工具，支持选中与调整。

### 3. 系统架构
- 采用 **UI - ViewModel - Service - Worker** 分层架构，逻辑清晰，易于扩展。
- 纯净 **PySide6** 实现，无 Qt 库冲突，兼容性好。

---

## 🛠️ 技术栈 (Tech Stack)

- **GUI 框架**: [PySide6](https://doc.qt.io/qtforpython/) (Qt for Python 官方库)
- **AI/CV 核心**: [Ultralytics YOLO](https://github.com/ultralytics/ultralytics), [OpenCV](https://opencv.org/)
- **数据存储**: [Peewee ORM](http://docs.peewee-orm.com/) (SQLite)
- **语言**: Python 3.10+

---

## 📦 安装与运行指南

### 1. 环境准备
建议使用 Anaconda 创建独立的虚拟环境（推荐 Python 3.10以获得最佳兼容性）。

```bash
# 创建环境
conda create -n yintu python=3.10 -y

# 激活环境
conda activate yintu
# 使用清华源加速安装
pip install PySide6 peewee opencv-python ultralytics numpy -i [https://pypi.tuna.tsinghua.edu.cn/simple](https://pypi.tuna.tsinghua.edu.cn/simple)
python main.py### 2. 运行
YinTu_Desktop/
├── main.py                     # 【入口】程序启动文件
├── data/                       # 【数据】存放 SQLite 数据库和抽帧结果
├── app/
│   ├── common/                 # 全局配置与日志
│   │   ├── config.py
│   │   └── logger.py
│   ├── models/                 # 数据库模型 (Peewee)
│   │   └── schema.py
│   ├── services/               # 业务逻辑层 (数据扫描、入库)
│   │   └── data_manager.py
│   ├── workers/                # 后台线程 (视频抽帧、AI推理)
│   │   ├── video_worker.py
│   │   └── ai_worker.py
│   └── ui/                     # 界面层
│       ├── main_window.py      # 主窗口框架
│       └── views/
│           ├── home_interface.py   # 首页
│           └── label_interface.py  # 核心标注工作台 (QGraphicsView)
