"""
问题单新建面板

提供问题单创建界面（嵌入主界面使用）
"""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from ..data.database_manager import DatabaseManager
from ..data.issue_dao import IssueDAO
from ..data.module_dao import ModuleDAO
from ..data.project_dao import ProjectDAO
from ..models.issue_model import Issue, IssueStatus
from .widgets.rich_text_editor import RichTextEditor


class CreateIssuePanel(QWidget):
    """
    创建问题单面板

    功能：
    - 收集问题单创建所需信息
    - 自动生成问题单号
    - 验证输入并创建问题单
    """

    # 信号定义
    issue_created = Signal(int)  # 问题单创建成功信号
    closed = Signal()            # 关闭面板信号

    def __init__(self, parent=None):
        """初始化面板"""
        super().__init__(parent)

        # 初始化数据访问对象
        self._db = DatabaseManager.get_instance()
        self._issue_dao = IssueDAO(self._db)
        self._module_dao = ModuleDAO(self._db)
        self._project_dao = ProjectDAO(self._db)

        # 设置面板
        self.setup_ui()
        self.setup_style()

    def setup_ui(self):
        """设置UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题栏
        title_bar = QHBoxLayout()

        self._title_label = QLabel("新建问题单")
        self._title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #27AE60;")
        title_bar.addWidget(self._title_label)

        title_bar.addStretch()

        self._close_btn = QPushButton("返回列表")
        self._close_btn.setObjectName("closePanelBtn")
        self._close_btn.clicked.connect(self._on_close)
        title_bar.addWidget(self._close_btn)

        layout.addLayout(title_bar)

        # 问题单号显示
        issue_no_layout = QHBoxLayout()
        issue_no_label = QLabel("问题单号:")
        issue_no_layout.addWidget(issue_no_label)
        self._issue_no_display = QLabel("(创建时自动生成)")
        self._issue_no_display.setStyleSheet("font-size: 14px; color: #888888;")
        issue_no_layout.addWidget(self._issue_no_display)
        issue_no_layout.addStretch()
        layout.addLayout(issue_no_layout)

        # 项目选择（必选）
        project_group = QWidget()
        project_group.setStyleSheet("background-color: #2E2E3E; border-radius: 8px; padding: 10px;")
        project_layout = QVBoxLayout(project_group)

        project_header = QHBoxLayout()
        project_label = QLabel("* 所属项目:")
        project_label.setStyleSheet("color: #E74C3C;")
        project_header.addWidget(project_label)
        project_header.addStretch()
        project_layout.addLayout(project_header)

        project_row = QHBoxLayout()
        self._project_combo = QComboBox()
        self._project_combo.setMinimumWidth(250)
        self._project_combo.currentIndexChanged.connect(self._on_project_changed)
        project_row.addWidget(self._project_combo)
        project_row.addStretch()
        project_layout.addLayout(project_row)

        layout.addWidget(project_group)

        # 简要描述
        title_group = QWidget()
        title_group.setStyleSheet("background-color: #2E2E3E; border-radius: 8px; padding: 10px;")
        title_layout = QVBoxLayout(title_group)

        title_header = QHBoxLayout()
        title_label = QLabel("* 简要描述:")
        title_label.setStyleSheet("color: #E74C3C;")
        title_header.addWidget(title_label)
        title_header.addStretch()
        title_layout.addLayout(title_header)

        self._title_input = QLineEdit()
        self._title_input.setPlaceholderText("请输入问题简要描述...")
        self._title_input.setMaxLength(100)
        title_layout.addWidget(self._title_input)

        layout.addWidget(title_group)

        # 详细描述
        desc_group = QWidget()
        desc_group.setStyleSheet("background-color: #2E2E3E; border-radius: 8px; padding: 10px;")
        desc_layout = QVBoxLayout(desc_group)

        desc_header = QHBoxLayout()
        desc_label = QLabel("* 详细描述:")
        desc_label.setStyleSheet("color: #E74C3C;")
        desc_header.addWidget(desc_label)
        desc_header.addStretch()
        desc_layout.addLayout(desc_header)

        self._description_editor = RichTextEditor(
            placeholder="请输入详细描述，支持粘贴图片...",
            issue_no="temp"
        )
        self._description_editor.set_min_height(1200)  # 可编辑区域高度加大
        desc_layout.addWidget(self._description_editor)

        layout.addWidget(desc_group)

        # 模块选择
        module_group = QWidget()
        module_group.setStyleSheet("background-color: #2E2E3E; border-radius: 8px; padding: 10px;")
        module_layout = QVBoxLayout(module_group)

        module_header = QHBoxLayout()
        module_label = QLabel("模块选择:")
        module_header.addWidget(module_label)
        module_header.addStretch()
        module_layout.addLayout(module_header)

        module_row = QHBoxLayout()
        self._module_combo = QComboBox()
        self._module_combo.addItem("无", None)
        self._module_combo.setMinimumWidth(250)
        module_row.addWidget(self._module_combo)
        module_row.addStretch()
        module_layout.addLayout(module_row)

        layout.addWidget(module_group)

        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._submit_btn = QPushButton("提交创建")
        self._submit_btn.setObjectName("submitBtn")
        self._submit_btn.clicked.connect(self._on_submit)
        btn_layout.addWidget(self._submit_btn)

        layout.addLayout(btn_layout)

        # 加载项目和模块
        self._load_projects()
        self._load_modules()

    def _load_projects(self):
        """加载项目列表"""
        projects = self._project_dao.get_all()
        self._project_combo.clear()
        for project in projects:
            name = f"★ {project.name}" if project.is_default else project.name
            self._project_combo.addItem(name, project.id)

        # 默认选择默认项目
        default_project = self._project_dao.get_default_project()
        if default_project:
            index = self._project_combo.findData(default_project.id)
            if index >= 0:
                self._project_combo.setCurrentIndex(index)

    def _on_project_changed(self, index):
        """项目切换后重新加载模块"""
        self._load_modules()

    def _load_modules(self):
        """加载当前项目的模块列表"""
        self._module_combo.clear()
        self._module_combo.addItem("无", None)

        project_id = self._project_combo.currentData()
        if project_id:
            modules = self._module_dao.get_by_project(project_id)
            for module in modules:
                self._module_combo.addItem(module.name, module.id)

    def setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            CreateIssuePanel {
                background-color: #1E1E2E;
            }

            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                outline: none;
            }

            QLabel:focus {
                outline: none;
                border: none;
            }

            QLineEdit {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                padding: 10px;
                color: #FFFFFF;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 2px solid #3498DB;
            }

            QComboBox {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                padding: 8px;
                color: #FFFFFF;
                min-width: 150px;
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

            QPushButton {
                background-color: #3E3E4E;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                color: #FFFFFF;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #4E4E5E;
            }

            QPushButton#submitBtn {
                background-color: #27AE60;
                font-weight: bold;
            }

            QPushButton#submitBtn:hover {
                background-color: #2ECC71;
            }

            QPushButton#submitBtn:pressed {
                background-color: #1E8449;
            }

            QPushButton#closePanelBtn {
                background-color: #3498DB;
            }

            QPushButton#closePanelBtn:hover {
                background-color: #2980B9;
            }
        """)

    def _generate_issue_no(self) -> str:
        """生成问题单号"""
        now = datetime.now()
        return "PR" + now.strftime("%Y%m%d%H%M%S")

    def _validate_input(self) -> tuple[bool, str]:
        """验证输入"""
        if not self._project_combo.currentData():
            return (False, "请选择所属项目")

        if not self._title_input.text().strip():
            return (False, "请输入简要描述")

        if not self._description_editor.get_plain_text().strip():
            return (False, "请输入详细描述")

        return (True, "")

    def _on_submit(self):
        """提交按钮点击"""
        valid, error_msg = self._validate_input()
        if not valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return

        try:
            # 生成问题单号
            issue_no = self._generate_issue_no()
            self._issue_no_display.setText(issue_no)
            self._issue_no_display.setStyleSheet("font-size: 14px; font-weight: bold; color: #3498DB;")

            # 更新编辑器的issue_no
            self._description_editor.set_issue_no(issue_no)

            # 处理详细描述中的图片
            description = self._description_editor.get_html_content()
            description = self._description_editor._image_manager.convert_to_relative_paths(description)

            # 获取项目ID和模块ID
            project_id = self._project_combo.currentData()
            module_id = self._module_combo.currentData()

            now = datetime.now()
            issue = Issue(
                issue_no=issue_no,
                title=self._title_input.text().strip(),
                description=description,
                module_id=module_id,
                project_id=project_id,
                status=IssueStatus.SUBMIT_TEST,
                created_at=now,
                updated_at=now,
                status_changed_at=now
            )

            issue_id = self._issue_dao.create(issue)

            self.issue_created.emit(issue_id)
            QMessageBox.information(self, "创建成功", f"问题单 {issue_no} 创建成功！")

            # 清空表单
            self._clear_form()
            self._on_close()

        except Exception as e:
            QMessageBox.critical(self, "创建失败", str(e))

    def _on_close(self):
        """关闭面板"""
        self.closed.emit()
        self._clear_form()

    def _clear_form(self):
        """清空表单"""
        self._title_input.clear()
        self._description_editor.clear_content()
        self._module_combo.setCurrentIndex(0)
        self._issue_no_display.setText("(创建时自动生成)")
        self._issue_no_display.setStyleSheet("font-size: 14px; color: #888888;")