"""
问题单管理系统

主程序入口
"""
import sys
import os

# 获取资源路径（支持 PyInstaller 打包）
def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 正常运行时的项目根目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# 获取数据路径（数据库等需要持久化的文件）
def get_data_path(relative_path):
    """获取数据文件的绝对路径（持久化目录）"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后，数据文件放在 exe 所在目录
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer

from src.ui.main_window import MainWindow


def main():
    """主函数"""
    # Windows 任务栏图标 - 必须在 QApplication 创建之前设置
    if sys.platform == "win32":
        import ctypes
        app_id = "IssueTrackingSystem.IssueTracker.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    # 创建应用
    app = QApplication(sys.argv)

    # 设置应用属性
    app.setApplicationName("问题单管理系统")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("IssueTrackingSystem")

    # 设置应用图标
    icon_path_ico = get_resource_path("assets/bug.ico")
    icon_path_png = get_resource_path("assets/bug.png")

    # Windows 任务栏优先使用 ICO 格式
    if os.path.exists(icon_path_ico):
        icon = QIcon(icon_path_ico)
    elif os.path.exists(icon_path_png):
        icon = QIcon(icon_path_png)
    else:
        icon = QIcon()

    if not icon.isNull():
        app.setWindowIcon(icon)

    # 创建主窗口
    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    # 默认最大化显示（保留标题栏按钮）
    window.showMaximized()

    # Windows 任务栏图标 - 稍后使用 win32gui 设置
    if sys.platform == "win32" and os.path.exists(icon_path_ico):
        import win32gui
        import win32con
        def set_taskbar_icon():
            hwnd = int(window.winId())
            hicon = win32gui.LoadImage(
                None,
                icon_path_ico,
                win32con.IMAGE_ICON,
                0, 0,
                win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            )
            win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, hicon)
            win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, hicon)
        QTimer.singleShot(100, set_taskbar_icon)

    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()