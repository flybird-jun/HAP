"""
主窗口模块

系统的主界面，使用页面切换模式，每个页面占据全部空间
"""
from datetime import datetime
from typing import List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QMenu, QStackedWidget
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QAction, QColor

from ..data.database_manager import DatabaseManager
from ..data.issue_dao import IssueDAO
from ..data.module_dao import ModuleDAO
from ..data.project_dao import ProjectDAO
from ..models.issue_model import Issue, IssueStatus
from ..models.project_model import Project
from .issue_detail_panel import IssueDetailPanel
from .create_issue_panel import CreateIssuePanel
from .module_manager_panel import ModuleManagerPanel
from .project_manager_panel import ProjectManagerPanel


class MainWindow(QMainWindow):
    """
    主窗口

    功能：
    - 使用页面切换模式
    - 问题单列表页面（默认首页）
    - 问题单详情页面（点击列表项进入）
    - 新建问题单页面（点击新建按钮进入）
    - 项目管理页面（点击项目管理按钮进入）
    - 模块管理页面（点击模块管理按钮进入）
    """

    # 页面索引
    PAGE_LIST = 0
    PAGE_DETAIL = 1
    PAGE_CREATE = 2
    PAGE_PROJECT = 3
    PAGE_MODULE = 4

    def __init__(self):
        """初始化主窗口"""
        super().__init__()

        # 初始化数据库
        self._db = DatabaseManager.get_instance()
        self._issue_dao = IssueDAO(self._db)
        self._module_dao = ModuleDAO(self._db)
        self._project_dao = ProjectDAO(self._db)

        # 当前显示的问题单列表
        self._current_issues: List[Issue] = []
        self._current_filter_status: int = -1
        self._current_search_keyword: str = ""
        self._current_project_id: int = None  # 当前选中的项目ID
        self._current_module_id: int = None   # 当前选中的模块ID

        # 设置窗口
        self.setWindowTitle("问题单管理系统")
        self.setMinimumSize(800, 600)

        self.setup_ui()
        self.setup_style()
        self.setup_connections()

        # 加载数据
        self.load_issues()

        # 设置定时器更新停留时间
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stay_duration)
        self._timer.start(60000)

    def setup_ui(self):
        """设置UI组件"""
        # 中心控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 使用堆叠布局切换页面
        self._stack = QStackedWidget()

        # ========== 页面1：问题单列表 ==========
        list_page = QWidget()
        list_layout = QVBoxLayout(list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(15)

        # 操作按钮行（过滤条件 + 项目过滤 + 模块过滤 + 统计信息在最左边，按钮紧随其后）
        action_row = QHBoxLayout()

        filter_label = QLabel("过滤条件:")
        action_row.addWidget(filter_label)

        self._project_combo = QComboBox()
        self._project_combo.setMinimumWidth(150)
        self._load_projects()
        action_row.addWidget(self._project_combo)

        self._module_combo = QComboBox()
        self._module_combo.setMinimumWidth(150)
        self._load_modules()
        action_row.addWidget(self._module_combo)

        action_row.addSpacing(20)

        self._statistics_label = QLabel("统计: 共 0 条")
        self._statistics_label.setStyleSheet("color: #888888; font-size: 14px;")
        action_row.addWidget(self._statistics_label)

        action_row.addSpacing(30)

        self._create_btn = QPushButton("新建问题单")
        self._create_btn.setObjectName("primaryBtn")
        action_row.addWidget(self._create_btn)

        self._module_btn = QPushButton("模块管理")
        self._module_btn.setObjectName("secondaryBtn")
        action_row.addWidget(self._module_btn)

        self._project_btn = QPushButton("项目管理")
        self._project_btn.setObjectName("secondaryBtn")
        action_row.addWidget(self._project_btn)

        action_row.addStretch()

        list_layout.addLayout(action_row)

        # 搜索和过滤区域
        search_layout = QHBoxLayout()

        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 16px;")
        search_layout.addWidget(search_label)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索问题单号、标题、描述...")
        self._search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self._search_input, stretch=1)

        self._status_filter = QComboBox()
        self._status_filter.addItems(["全部", "提交测试", "开发中", "归档", "关闭"])
        self._status_filter.setCurrentIndex(0)
        search_layout.addWidget(self._status_filter)

        list_layout.addLayout(search_layout)

        # 问题单列表表格
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["问题单号", "简要描述", "状态", "停留时间"])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(50)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self._table.setColumnWidth(0, 180)
        self._table.setColumnWidth(2, 140)
        self._table.setColumnWidth(3, 160)

        for col in range(4):
            header_item = self._table.horizontalHeaderItem(col)
            if header_item:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        list_layout.addWidget(self._table)

        self._stack.addWidget(list_page)

        # ========== 页面2：问题单详情 ==========
        self._detail_panel = IssueDetailPanel()
        self._detail_panel.issue_updated.connect(self.on_issue_updated)
        self._detail_panel.issue_deleted.connect(self.on_issue_deleted)
        self._detail_panel.closed.connect(self._show_list_page)
        self._stack.addWidget(self._detail_panel)

        # ========== 页面3：新建问题单 ==========
        self._create_panel = CreateIssuePanel()
        self._create_panel.issue_created.connect(self.on_issue_created)
        self._create_panel.closed.connect(self._show_list_page)
        self._stack.addWidget(self._create_panel)

        # ========== 页面4：项目管理 ==========
        self._project_panel = ProjectManagerPanel()
        self._project_panel.projects_updated.connect(self._on_projects_updated)
        self._project_panel.closed.connect(self._show_list_page)
        self._stack.addWidget(self._project_panel)

        # ========== 页面5：模块管理 ==========
        self._module_panel = ModuleManagerPanel()
        self._module_panel.closed.connect(self._show_list_page)
        self._stack.addWidget(self._module_panel)

        main_layout.addWidget(self._stack)

    def setup_style(self):
        """设置窗口样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E2E;
            }

            QWidget {
                background-color: #1E1E2E;
                color: #FFFFFF;
            }

            *:focus {
                outline: none;
                border: none;
            }

            QLabel {
                outline: none;
            }

            QLineEdit {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                padding: 12px 18px;
                color: #FFFFFF;
                font-size: 15px;
            }

            QLineEdit:focus {
                border: 2px solid #3498DB;
            }

            QComboBox {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                padding: 10px 14px;
                color: #FFFFFF;
                font-size: 15px;
                min-width: 120px;
            }

            QComboBox:hover {
                border: 1px solid #3498DB;
            }

            QComboBox::drop-down {
                border: none;
                width: 25px;
            }

            QComboBox QAbstractItemView {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                selection-background-color: #3498DB;
                color: #FFFFFF;
            }

            QTableWidget {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                gridline-color: transparent;
                color: #FFFFFF;
                font-size: 15px;
            }

            QTableWidget::item {
                padding: 16px 10px;
                border-bottom: 1px solid #3E3E4E;
            }

            QTableWidget::item:selected {
                background-color: #3498DB;
                color: #FFFFFF;
            }

            QTableWidget::item:hover {
                background-color: #3E3E4E;
            }

            QHeaderView::section {
                background-color: #1E1E2E;
                border: none;
                border-bottom: 2px solid #3498DB;
                border-right: 1px dashed #3E3E4E;
                padding: 14px 10px;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: bold;
            }

            QHeaderView::section:last {
                border-right: none;
            }

            QPushButton {
                background-color: #3E3E4E;
                border: none;
                border-radius: 8px;
                padding: 14px 24px;
                color: #FFFFFF;
                font-size: 15px;
            }

            QPushButton:hover {
                background-color: #4E4E5E;
            }

            QPushButton:pressed {
                background-color: #5E5E6E;
            }

            QPushButton#primaryBtn {
                background-color: #3498DB;
            }

            QPushButton#primaryBtn:hover {
                background-color: #2980B9;
            }

            QPushButton#secondaryBtn {
                background-color: #27AE60;
            }

            QPushButton#secondaryBtn:hover {
                background-color: #2ECC71;
            }

            QScrollBar:vertical {
                background-color: #2E2E3E;
                width: 10px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background-color: #4E4E5E;
                border-radius: 5px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #5E5E6E;
            }
        """)

    def setup_connections(self):
        """设置信号连接"""
        self._project_combo.currentIndexChanged.connect(self._on_project_changed)
        self._module_combo.currentIndexChanged.connect(self._on_module_changed)
        self._project_btn.clicked.connect(self._show_project_page)
        self._search_input.textChanged.connect(self.on_search)
        self._status_filter.currentIndexChanged.connect(self.on_filter)
        self._create_btn.clicked.connect(self.on_create_issue)
        self._module_btn.clicked.connect(self._show_module_page)
        self._table.doubleClicked.connect(self.on_issue_double_clicked)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self.on_issue_context_menu)

    def _show_list_page(self):
        """显示列表页面"""
        self._stack.setCurrentIndex(self.PAGE_LIST)
        self.setWindowTitle("问题单管理系统")

    def _load_projects(self):
        """加载项目列表"""
        projects = self._project_dao.get_all()
        self._project_combo.clear()

        # 添加"全部项目"选项
        self._project_combo.addItem("全部项目", None)

        for project in projects:
            self._project_combo.addItem(project.name, project.id)

        # 默认选择"全部项目"
        self._project_combo.setCurrentIndex(0)
        self._current_project_id = None

    def _load_modules(self):
        """加载模块列表"""
        self._module_combo.clear()
        self._module_combo.addItem("全部模块", None)

        # 根据选中的项目过滤模块
        project_id = self._current_project_id
        if project_id:
            modules = self._module_dao.get_by_project(project_id)
        else:
            modules = self._module_dao.get_all()

        for module in modules:
            self._module_combo.addItem(module.name, module.id)

        # 默认选择"全部模块"
        self._module_combo.setCurrentIndex(0)
        self._current_module_id = None

    def _on_project_changed(self, index):
        """项目切换事件"""
        self._current_project_id = self._project_combo.currentData()
        self._search_input.clear()
        self._current_search_keyword = ""
        self._current_filter_status = -1
        self._status_filter.setCurrentIndex(0)
        # 更新模块列表
        self._load_modules()
        self.load_issues()

    def _on_module_changed(self, index):
        """模块切换事件"""
        self._current_module_id = self._module_combo.currentData()
        self._search_input.clear()
        self._current_search_keyword = ""
        self._current_filter_status = -1
        self._status_filter.setCurrentIndex(0)
        self.load_issues()

    def _show_project_page(self):
        """显示项目管理页面"""
        self.setWindowTitle("项目管理")
        self._project_panel.load_projects()
        self._stack.setCurrentIndex(self.PAGE_PROJECT)

    def _show_module_page(self):
        """显示模块管理页面"""
        self.setWindowTitle("模块管理")
        self._module_panel.load_modules()
        self._stack.setCurrentIndex(self.PAGE_MODULE)

    def _on_projects_updated(self):
        """项目列表更新回调"""
        self._load_projects()
        self.load_issues()

    def _show_detail_page(self, issue_id: int):
        """显示详情页面"""
        issue = self._issue_dao.get_by_id(issue_id)
        if issue:
            self.setWindowTitle(f"问题单详情 - {issue.issue_no}")
            self._detail_panel.load_issue(issue_id)
            self._stack.setCurrentIndex(self.PAGE_DETAIL)

    def _show_create_page(self):
        """显示新建页面"""
        self.setWindowTitle("新建问题单")
        self._stack.setCurrentIndex(self.PAGE_CREATE)

    def load_issues(self):
        """加载问题单列表"""
        # 根据项目和模块过滤
        if self._current_project_id and self._current_module_id:
            # 同时过滤项目和模块
            self._current_issues = self._issue_dao.get_by_project_and_module(
                self._current_project_id, self._current_module_id
            )
        elif self._current_module_id:
            # 只过滤模块
            self._current_issues = self._issue_dao.get_by_module(self._current_module_id)
        elif self._current_project_id:
            # 只过滤项目
            if self._current_search_keyword:
                self._current_issues = self._issue_dao.search(
                    self._current_search_keyword, self._current_project_id
                )
            elif self._current_filter_status >= 0:
                self._current_issues = self._issue_dao.get_by_project_and_status(
                    self._current_project_id, self._current_filter_status
                )
            else:
                self._current_issues = self._issue_dao.get_by_project(self._current_project_id)
        else:
            # 全部项目
            if self._current_search_keyword:
                self._current_issues = self._issue_dao.search(self._current_search_keyword)
            elif self._current_filter_status >= 0:
                self._current_issues = self._issue_dao.get_by_status(self._current_filter_status)
            else:
                self._current_issues = self._issue_dao.get_all()

        self.refresh_table()
        self.update_statistics()

    def refresh_table(self):
        """刷新表格数据"""
        self._table.setRowCount(len(self._current_issues))

        for row, issue in enumerate(self._current_issues):
            issue_no_item = QTableWidgetItem(issue.issue_no)
            issue_no_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._table.setItem(row, 0, issue_no_item)

            title_item = QTableWidgetItem(issue.title)
            title_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._table.setItem(row, 1, title_item)

            status_text = self.format_status(issue.status)
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._table.setItem(row, 2, status_item)

            stay_duration = issue.calculate_stay_duration()
            duration_item = QTableWidgetItem(stay_duration)
            duration_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._table.setItem(row, 3, duration_item)

            color = self.get_status_color(issue.status)
            if color:
                for col in range(4):
                    item = self._table.item(row, col)
                    if item:
                        item.setBackground(QColor(color))

    def update_statistics(self):
        """更新统计信息"""
        total = len(self._current_issues)
        status_counts = self._issue_dao.count_by_status(self._current_project_id)

        developing_count = status_counts.get(IssueStatus.DEVELOPING, 0)
        archived_count = status_counts.get(IssueStatus.ARCHIVED, 0)

        status_text = ""
        if developing_count > 0:
            status_text += f"开发中{developing_count}"
        if archived_count > 0:
            if status_text:
                status_text += "/"
            status_text += f"归档{archived_count}"

        if status_text:
            self._statistics_label.setText(f"统计: 共{total}条 ({status_text})")
        else:
            self._statistics_label.setText(f"统计: 共{total}条")

    def _update_stay_duration(self):
        """定时更新停留时间"""
        for row, issue in enumerate(self._current_issues):
            stay_duration = issue.calculate_stay_duration()
            duration_item = QTableWidgetItem(stay_duration)
            duration_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._table.setItem(row, 3, duration_item)

    def format_status(self, status: int) -> str:
        """格式化状态显示文本"""
        status_map = {
            IssueStatus.SUBMIT_TEST: "⚪ 提交测试",
            IssueStatus.DEVELOPING: "🔵 开发中",
            IssueStatus.ARCHIVED: "🟡 归档",
            IssueStatus.CLOSED: "⚫ 关闭"
        }
        return status_map.get(status, "未知")

    def get_status_color(self, status: int) -> str:
        """获取状态对应的颜色"""
        color_map = {
            IssueStatus.SUBMIT_TEST: "",
            IssueStatus.DEVELOPING: "#2980B9",
            IssueStatus.ARCHIVED: "#B7950B",
            IssueStatus.CLOSED: "#1C2833"
        }
        return color_map.get(status, "")

    def on_search(self, keyword: str):
        """搜索事件处理"""
        self._current_search_keyword = keyword.strip()
        self.load_issues()

    def on_filter(self, index: int):
        """状态过滤事件处理"""
        status_map = {-1: -1, 0: -1, 1: 0, 2: 1, 3: 2, 4: 3}
        self._current_filter_status = status_map.get(index, -1)
        self._search_input.clear()
        self._current_search_keyword = ""
        self.load_issues()

    def on_create_issue(self):
        """新建问题单按钮点击"""
        self._show_create_page()

    def on_issue_double_clicked(self, index):
        """双击问题单行打开详情"""
        row = index.row()
        if row < len(self._current_issues):
            issue = self._current_issues[row]
            self._show_detail_page(issue.id)

    def on_issue_context_menu(self, position):
        """右键菜单"""
        row = self._table.rowAt(position.y())
        if row < 0:
            return

        issue = self._current_issues[row]

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                color: #FFFFFF;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3498DB;
            }
        """)

        open_action = QAction("查看详情", self)
        open_action.triggered.connect(lambda: self._show_detail_page(issue.id))
        menu.addAction(open_action)

        if issue.status == IssueStatus.SUBMIT_TEST:
            menu.addSeparator()
            delete_action = QAction("删除问题单", self)
            delete_action.triggered.connect(lambda: self._delete_issue(issue.id))
            menu.addAction(delete_action)

        menu.exec(self._table.viewport().mapToGlobal(position))

    def _delete_issue(self, issue_id: int):
        """删除问题单"""
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这个问题单吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self._issue_dao.delete(issue_id):
                self.on_issue_deleted(issue_id)
            else:
                QMessageBox.warning(self, "删除失败", "只有提交测试状态的问题单才能删除")

    def on_issue_created(self, issue_id: int):
        """问题单创建成功回调"""
        self.load_issues()
        self._show_detail_page(issue_id)

    def on_issue_updated(self, issue_id: int):
        """问题单更新成功回调"""
        self.load_issues()

    def on_issue_deleted(self, issue_id: int):
        """问题单删除成功回调"""
        self.load_issues()
        self._show_list_page()

    def closeEvent(self, event):
        """窗口关闭事件"""
        self._timer.stop()
        self._db.close()
        event.accept()