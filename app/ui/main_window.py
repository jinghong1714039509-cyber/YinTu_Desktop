# app/ui/main_window.py
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

from qfluentwidgets import (FluentWindow, NavigationItemPosition, FluentIcon as FIF,
                            setTheme, Theme)

from app.ui.views.home_interface import HomeInterface

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle('YinTu Desktop')
        self.resize(1100, 750)
        
        # 设置暗色主题
        setTheme(Theme.DARK)
        
        # 初始化子页面
        self.homeInterface = HomeInterface(self)
        self.labelInterface = HomeInterface(self) # 占位
        self.settingInterface = HomeInterface(self) # 占位
        
        self.initNavigation()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '仪表盘', NavigationItemPosition.TOP)
        self.addSubInterface(self.labelInterface, FIF.EDIT, '标注工作台', NavigationItemPosition.TOP)
        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)