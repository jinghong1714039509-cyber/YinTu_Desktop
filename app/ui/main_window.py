from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon as FIF, setTheme, Theme
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

        # 初始化子页面
        self.homeInterface = HomeInterface(self)
        self.labelInterface = LabelInterface(self)
        
        # 信号连接
        self.homeInterface.project_selected.connect(self.on_project_loaded)

        self.initNavigation()

    def initNavigation(self):
        self.addSubInterface(self.homeInterface, FIF.HOME, '项目管理')
        self.addSubInterface(self.labelInterface, FIF.EDIT, '标注工作台')
        
        # 默认隐藏标注页，直到选择了项目
        # self.navigationInterface.item(FIF.EDIT).setHidden(True) 

    def on_project_loaded(self, path):
        logger.info(f"项目已加载: {path}")
        # 这里应该调用 DataManager 扫描路径下的文件入库
        # 然后跳转到标注页面
        self.switchTo(self.labelInterface)
        self.labelInterface.load_image(path) # 暂时仅作为测试，这里应该传具体的图片文件