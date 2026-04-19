"""
模块管理面板模块

提供模块管理界面（嵌入主界面使用）
"""
from typing import List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QComboBox
)
from PySide6.QtCore import Signal, Qt

from ..data.database_manager import DatabaseManager
from ..data.module_dao import ModuleDAO
from ..data.project_dao import ProjectDAO
from ..models.module_model import Module
from ..models.project_model import Project


class ModuleManagerPanel(QWidget):
    """
    模块管理面板

    功能：
    - 展示模块列表
    - 添加新模块
    - 编辑模块名称
    - 删除模块
    """

    # 信号定义
    closed = Signal()  # 关闭面板信号

    def __init__(self, parent=None):
        """初始化面板"""
        super().__init__(parent)

        # 初始化数据访问对象
        self._db = DatabaseManager.get_instance()
        self._module_dao = ModuleDAO(self._db)
        self._project_dao = ProjectDAO(self._db)

        # 当前模块列表
        self._modules: List[Module] = []

        self.setup_ui()
        self.setup_style()
        self.load_modules()

    def setup_ui(self):
        """设置UI组件"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题栏
        title_bar = QHBoxLayout()

        self._title_label = QLabel("模块管理")
        self._title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #27AE60;")
        title_bar.addWidget(self._title_label)

        title_bar.addStretch()

        self._close_btn = QPushButton("返回列表")
        self._close_btn.setObjectName("closePanelBtn")
        self._close_btn.clicked.connect(self._on_close)
        title_bar.addWidget(self._close_btn)

        layout.addLayout(title_bar)

        # 项目过滤区域
        filter_group = QWidget()
        filter_group.setObjectName("filterGroup")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setContentsMargins(10, 10, 10, 10)

        filter_label = QLabel("筛选项目:")
        filter_layout.addWidget(filter_label)

        self._project_filter_combo = QComboBox()
        self._project_filter_combo.addItem("全部项目", None)
        self._project_filter_combo.setMinimumWidth(150)
        self._load_projects_for_filter()
        self._project_filter_combo.currentIndexChanged.connect(self._on_project_filter_changed)
        filter_layout.addWidget(self._project_filter_combo)
        filter_layout.addStretch()

        layout.addWidget(filter_group)

        # 添加模块区域
        add_group = QWidget()
        add_group.setObjectName("addGroup")
        add_layout = QHBoxLayout(add_group)
        add_layout.setContentsMargins(10, 10, 10, 10)

        project_label = QLabel("* 所属项目:")
        project_label.setStyleSheet("color: #E74C3C;")
        add_layout.addWidget(project_label)

        self._project_combo = QComboBox()
        self._project_combo.setMinimumWidth(150)
        self._load_projects()
        add_layout.addWidget(self._project_combo)

        module_label = QLabel("模块名称:")
        add_layout.addWidget(module_label)

        self._module_input = QLineEdit()
        self._module_input.setPlaceholderText("请输入模块名称...")
        self._module_input.setMaxLength(50)
        add_layout.addWidget(self._module_input, stretch=1)

        self._add_btn = QPushButton("添加模块")
        self._add_btn.setObjectName("addBtn")
        self._add_btn.clicked.connect(self.on_add_module)
        add_layout.addWidget(self._add_btn)

        layout.addWidget(add_group)

        # 模块列表表格
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["序号", "模块名称", "所属项目", "关联问题数", "操作"])
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.setShowGrid(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(60)

        # 设置列宽
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(1, 150)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 150)

        layout.addWidget(self._table, stretch=1)

        # 统计信息
        self._statistics_label = QLabel("统计: 共 0 个模块")
        self._statistics_label.setStyleSheet("color: #888888; font-size: 14px;")
        layout.addWidget(self._statistics_label)

    def setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            ModuleManagerPanel {
                background-color: #1E1E2E;
            }

            QWidget#addGroup, QWidget#filterGroup {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
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
                min-width: 120px;
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
                padding: 12px 20px;
                color: #FFFFFF;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #4E4E5E;
            }

            QPushButton#addBtn {
                background-color: #27AE60;
                font-weight: bold;
            }

            QPushButton#addBtn:hover {
                background-color: #2ECC71;
            }

            QPushButton#editBtn {
                background-color: #3498DB;
                padding: 8px 16px;
                font-size: 14px;
            }

            QPushButton#editBtn:hover {
                background-color: #2980B9;
            }

            QPushButton#deleteBtn {
                background-color: #E74C3C;
                padding: 8px 16px;
                font-size: 14px;
            }

            QPushButton#deleteBtn:hover {
                background-color: #C0392B;
            }

            QPushButton#closePanelBtn {
                background-color: #3498DB;
            }

            QPushButton#closePanelBtn:hover {
                background-color: #2980B9;
            }

            QTableWidget {
                background-color: #2E2E3E;
                border: 1px solid #3E3E4E;
                border-radius: 8px;
                gridline-color: transparent;
                color: #FFFFFF;
                font-size: 14px;
            }

            QTableWidget::item {
                padding: 10px 8px;
                border-bottom: 1px solid #3E3E4E;
                background-color: #2E2E3E;
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
                padding: 12px 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }
        """)

    def _on_close(self):
        """关闭面板"""
        self.closed.emit()

    def _load_projects(self):
        """加载项目列表（用于添加模块时选择）"""
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

    def _load_projects_for_filter(self):
        """加载项目列表（用于筛选）"""
        projects = self._project_dao.get_all()
        self._project_filter_combo.clear()
        self._project_filter_combo.addItem("全部项目", None)
        for project in projects:
            self._project_filter_combo.addItem(project.name, project.id)

    def _on_project_filter_changed(self, index):
        """项目过滤切换"""
        self.load_modules()

    def load_modules(self):
        """加载模块列表"""
        project_id = self._project_filter_combo.currentData()
        if project_id:
            self._modules = self._module_dao.get_by_project_with_issue_count(project_id)
        else:
            self._modules = self._module_dao.get_all_with_issue_count()
        self.refresh_table()
        self.update_statistics()

    def refresh_table(self):
        """刷新表格数据"""
        self._table.setRowCount(len(self._modules))

        for row, module in enumerate(self._modules):
            # 序号
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, index_item)

            # 模块名称
            name_item = QTableWidgetItem(module.name)
            self._table.setItem(row, 1, name_item)

            # 所属项目
            project_item = QTableWidgetItem(module.project_name or "未知")
            self._table.setItem(row, 2, project_item)

            # 关联问题数
            count_item = QTableWidgetItem(str(module.issue_count))
            count_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 3, count_item)

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 4, 4, 4)
            btn_layout.setSpacing(4)

            edit_btn = QPushButton("编辑")
            edit_btn.setObjectName("editBtn")
            edit_btn.clicked.connect(lambda checked, m=module: self.on_edit_module(m))
            btn_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setObjectName("deleteBtn")
            delete_btn.clicked.connect(lambda checked, m=module: self.on_delete_module(m))
            btn_layout.addWidget(delete_btn)

            self._table.setCellWidget(row, 4, btn_widget)

    def update_statistics(self):
        """更新统计信息"""
        total_modules = len(self._modules)
        total_issues = sum(m.issue_count for m in self._modules)
        self._statistics_label.setText(f"统计: 共 {total_modules} 个模块，关联 {total_issues} 个问题单")

    def on_add_module(self):
        """添加模块"""
        name = self._module_input.text().strip()
        project_id = self._project_combo.currentData()

        # 验证项目
        if not project_id:
            QMessageBox.warning(self, "输入错误", "请选择所属项目")
            return

        # 验证名称
        valid, error_msg = self.validate_module_name(name, project_id)
        if not valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return

        try:
            self._module_dao.create(name, project_id)
            self._module_input.clear()
            self.load_modules()
            QMessageBox.information(self, "添加成功", f"模块 '{name}' 已添加！")

        except Exception as e:
            QMessageBox.warning(self, "添加失败", str(e))

    def on_edit_module(self, module: Module):
        """编辑模块"""
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "编辑模块", "请输入新的模块名称:",
            QLineEdit.Normal, module.name
        )

        if not ok:
            return

        new_name = new_name.strip()

        # 验证名称（项目内唯一）
        valid, error_msg = self.validate_module_name(new_name, module.project_id, exclude_id=module.id)
        if not valid:
            QMessageBox.warning(self, "输入错误", error_msg)
            return

        try:
            self._module_dao.update(module.id, new_name)
            self.load_modules()
            QMessageBox.information(self, "编辑成功", f"模块已更新为 '{new_name}'！")

        except Exception as e:
            QMessageBox.warning(self, "编辑失败", str(e))

    def on_delete_module(self, module: Module):
        """删除模块"""
        # 确认删除
        if module.issue_count > 0:
            msg = f"模块 '{module.name}' 关联了 {module.issue_count} 个问题单。\n删除后，这些问题单将取消模块关联。\n是否继续删除？"
        else:
            msg = f"确定要删除模块 '{module.name}' 吗？"

        reply = QMessageBox.question(
            self, "确认删除", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self._module_dao.delete(module.id)
            self.load_modules()
            QMessageBox.information(self, "删除成功", f"模块 '{module.name}' 已删除！")

        except Exception as e:
            QMessageBox.warning(self, "删除失败", str(e))

    def validate_module_name(self, name: str, project_id: int = None, exclude_id: int = None) -> tuple[bool, str]:
        """验证模块名称"""
        if not name:
            return (False, "模块名称不能为空")

        if len(name) > 50:
            return (False, "模块名称不能超过50个字符")

        if project_id and self._module_dao.is_name_exists(name, project_id, exclude_id):
            return (False, f"该项目内模块名称 '{name}' 已存在")

        return (True, "")