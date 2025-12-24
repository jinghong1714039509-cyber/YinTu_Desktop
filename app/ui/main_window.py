from __future__ import annotations

from pathlib import Path

from qfluentwidgets import FluentWindow, FluentIcon as FIF, setTheme, Theme

from app.ui.views.home_interface import HomeInterface
from app.ui.views.label_interface import LabelInterface
from app.services.data_manager import DataManager
from app.common.logger import logger


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('YinTu Desktop - AI 智能标注平台')
        self.resize(1200, 800)
        setTheme(Theme.DARK)

        self.homeInterface = HomeInterface(self)
        self.labelInterface = LabelInterface(self)

        # 信号连接
        self.homeInterface.project_selected.connect(self.on_project_loaded)

        self.initNavigation()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '项目管理')
        self.addSubInterface(self.labelInterface, FIF.EDIT, '标注工作台')

    def on_project_loaded(self, path: str):
        """用户选择项目目录后：创建/加载项目 -> 同步任务 -> 进入工作台"""
        folder = str(Path(path).resolve())
        logger.info(f"项目已选择: {folder}")

        project = DataManager.get_or_create_project(folder)
        added = DataManager.sync_media_from_folder(project, folder)
        logger.info(f"任务同步完成，新增任务: {added}")

        self.labelInterface.set_project(project.id)
        self.switchTo(self.labelInterface)
