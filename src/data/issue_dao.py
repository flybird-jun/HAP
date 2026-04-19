"""
问题单数据访问模块

负责问题单的增删改查操作
"""
import sqlite3
from typing import List, Optional
from datetime import datetime

from .database_manager import DatabaseManager
from ..models.issue_model import Issue, IssueStatus


class IssueDAO:
    """
    问题单数据访问对象

    功能：
    - 问题单的CRUD操作
    - 状态流转处理
    - 搜索和过滤查询
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化DAO

        Args:
            db_manager: 数据库管理器实例，如果为None则自动获取
        """
        self._db = db_manager or DatabaseManager.get_instance()

    def create(self, issue: Issue) -> int:
        """
        创建问题单

        Args:
            issue: 问题单数据模型

        Returns:
            新创建的问题单ID

        Raises:
            ValueError: 必填字段为空
            sqlite3.IntegrityError: 问题单号重复
        """
        # 验证必填字段
        if not issue.issue_no:
            raise ValueError("问题单号不能为空")
        if not issue.title:
            raise ValueError("简要描述不能为空")
        if not issue.project_id:
            raise ValueError("必须选择所属项目")

        # 设置时间
        now = self._db.get_timestamp()
        if issue.created_at is None:
            issue.created_at = datetime.now()
        if issue.updated_at is None:
            issue.updated_at = datetime.now()
        if issue.status_changed_at is None:
            issue.status_changed_at = datetime.now()

        sql = """
            INSERT INTO issue (
                issue_no, title, description, module_id, project_id, status,
                root_cause, solution, self_test, archive_test,
                created_at, updated_at, status_changed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            issue.issue_no,
            issue.title,
            issue.description,
            issue.module_id,
            issue.project_id,
            int(issue.status),
            issue.root_cause,
            issue.solution,
            issue.self_test,
            issue.archive_test,
            issue.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            issue.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            issue.status_changed_at.strftime("%Y-%m-%d %H:%M:%S")
        )

        cursor = self._db.execute(sql, params)
        self._db.commit()
        return cursor.lastrowid

    def get_by_id(self, issue_id: int) -> Optional[Issue]:
        """
        根据ID获取问题单

        Args:
            issue_id: 问题单ID

        Returns:
            问题单模型，不存在返回None
        """
        sql = """
            SELECT i.*, m.name as module_name, p.name as project_name
            FROM issue i
            LEFT JOIN module m ON i.module_id = m.id
            LEFT JOIN project p ON i.project_id = p.id
            WHERE i.id = ?
        """
        data = self._db.fetchone(sql, (issue_id,))
        if data:
            return Issue.from_dict(data)
        return None

    def get_by_issue_no(self, issue_no: str) -> Optional[Issue]:
        """
        根据问题单号获取问题单

        Args:
            issue_no: 问题单号

        Returns:
            问题单模型，不存在返回None
        """
        sql = """
            SELECT i.*, m.name as module_name, p.name as project_name
            FROM issue i
            LEFT JOIN module m ON i.module_id = m.id
            LEFT JOIN project p ON i.project_id = p.id
            WHERE i.issue_no = ?
        """
        data = self._db.fetchone(sql, (issue_no,))
        if data:
            return Issue.from_dict(data)
        return None

    def get_all(self) -> List[Issue]:
        """
        获取所有问题单

        Returns:
            问题单列表，按创建时间倒序
        """
        sql = """
            SELECT i.*, m.name as module_name, p.name as project_name
            FROM issue i
            LEFT JOIN module m ON i.module_id = m.id
            LEFT JOIN project p ON i.project_id = p.id
            ORDER BY i.created_at DESC
        """
        data_list = self._db.fetchall(sql)
        return [Issue.from_dict(data) for data in data_list]

    def get_by_project(self, project_id: int) -> List[Issue]:
        """
        获取指定项目的问题单列表

        Args:
            project_id: 项目ID

        Returns:
            该项目的问题单列表
        """
        sql = """
            SELECT i.*, m.name as module_name, p.name as project_name
            FROM issue i
            LEFT JOIN module m ON i.module_id = m.id
            LEFT JOIN project p ON i.project_id = p.id
            WHERE i.project_id = ?
            ORDER BY i.created_at DESC
        """
        data_list = self._db.fetchall(sql, (project_id,))
        return [Issue.from_dict(data) for data in data_list]

    def get_by_status(self, status: int) -> List[Issue]:
        """
        根据状态获取问题单列表

        Args:
            status: 状态码

        Returns:
            符合条件的问题单列表
        """
        sql = """
            SELECT i.*, m.name as module_name, p.name as project_name
            FROM issue i
            LEFT JOIN module m ON i.module_id = m.id
            LEFT JOIN project p ON i.project_id = p.id
            WHERE i.status = ?
            ORDER BY i.created_at DESC
        """
        data_list = self._db.fetchall(sql, (status,))
        return [Issue.from_dict(data) for data in data_list]

    def get_by_project_and_status(self, project_id: int, status: int) -> List[Issue]:
        """
        获取指定项目指定状态的问题单列表

        Args:
            project_id: 项目ID
            status: 状态码

        Returns:
            符合条件的问题单列表
        """
        sql = """
            SELECT i.*, m.name as module_name, p.name as project_name
            FROM issue i
            LEFT JOIN module m ON i.module_id = m.id
            LEFT JOIN project p ON i.project_id = p.id
            WHERE i.project_id = ? AND i.status = ?
            ORDER BY i.created_at DESC
        """
        data_list = self._db.fetchall(sql, (project_id, status))
        return [Issue.from_dict(data) for data in data_list]

    def get_by_module(self, module_id: int) -> List[Issue]:
        """
        获取指定模块的问题单列表

        Args:
            module_id: 模块ID

        Returns:
            该模块的问题单列表
        """
        sql = """
            SELECT i.*, m.name as module_name, p.name as project_name
            FROM issue i
            LEFT JOIN module m ON i.module_id = m.id
            LEFT JOIN project p ON i.project_id = p.id
            WHERE i.module_id = ?
            ORDER BY i.created_at DESC
        """
        data_list = self._db.fetchall(sql, (module_id,))
        return [Issue.from_dict(data) for data in data_list]

    def get_by_project_and_module(self, project_id: int, module_id: int) -> List[Issue]:
        """
        获取指定项目和模块的问题单列表

        Args:
            project_id: 项目ID
            module_id: 模块ID

        Returns:
            符合条件的问题单列表
        """
        sql = """
            SELECT i.*, m.name as module_name, p.name as project_name
            FROM issue i
            LEFT JOIN module m ON i.module_id = m.id
            LEFT JOIN project p ON i.project_id = p.id
            WHERE i.project_id = ? AND i.module_id = ?
            ORDER BY i.created_at DESC
        """
        data_list = self._db.fetchall(sql, (project_id, module_id))
        return [Issue.from_dict(data) for data in data_list]

    def update(self, issue: Issue) -> bool:
        """
        更新问题单

        Args:
            issue: 更新后的问题单模型

        Returns:
            更新是否成功
        """
        if issue.id is None:
            return False

        issue.updated_at = datetime.now()

        sql = """
            UPDATE issue SET
                title = ?,
                description = ?,
                module_id = ?,
                project_id = ?,
                status = ?,
                root_cause = ?,
                solution = ?,
                self_test = ?,
                archive_test = ?,
                updated_at = ?,
                status_changed_at = ?
            WHERE id = ?
        """

        params = (
            issue.title,
            issue.description,
            issue.module_id,
            issue.project_id,
            int(issue.status),
            issue.root_cause,
            issue.solution,
            issue.self_test,
            issue.archive_test,
            issue.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            issue.status_changed_at.strftime("%Y-%m-%d %H:%M:%S"),
            issue.id
        )

        self._db.execute(sql, params)
        self._db.commit()
        return True

    def delete(self, issue_id: int) -> bool:
        """
        删除问题单

        Args:
            issue_id: 问题单ID

        Returns:
            删除是否成功
        """
        # 先检查问题单是否存在
        issue = self.get_by_id(issue_id)
        if issue is None:
            return False

        # 只有提交测试状态的问题单可以删除
        if issue.status != IssueStatus.SUBMIT_TEST:
            return False

        sql = "DELETE FROM issue WHERE id = ?"
        self._db.execute(sql, (issue_id,))
        self._db.commit()
        return True

    def search(self, keyword: str, project_id: int = None) -> List[Issue]:
        """
        搜索问题单

        Args:
            keyword: 搜索关键词（匹配单号、标题、描述）
            project_id: 项目ID（可选，用于项目内搜索）

        Returns:
            匹配的问题单列表
        """
        pattern = f"%{keyword}%"
        if project_id:
            sql = """
                SELECT i.*, m.name as module_name, p.name as project_name
                FROM issue i
                LEFT JOIN module m ON i.module_id = m.id
                LEFT JOIN project p ON i.project_id = p.id
                WHERE i.project_id = ? AND (i.issue_no LIKE ? OR i.title LIKE ? OR i.description LIKE ?)
                ORDER BY i.created_at DESC
            """
            data_list = self._db.fetchall(sql, (project_id, pattern, pattern, pattern))
        else:
            sql = """
                SELECT i.*, m.name as module_name, p.name as project_name
                FROM issue i
                LEFT JOIN module m ON i.module_id = m.id
                LEFT JOIN project p ON i.project_id = p.id
                WHERE i.issue_no LIKE ? OR i.title LIKE ? OR i.description LIKE ?
                ORDER BY i.created_at DESC
            """
            data_list = self._db.fetchall(sql, (pattern, pattern, pattern))
        return [Issue.from_dict(data) for data in data_list]

    def update_status(self, issue_id: int, new_status: int) -> bool:
        """
        更新问题单状态

        Args:
            issue_id: 问题单ID
            new_status: 新状态码

        Returns:
            更新是否成功
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = """
            UPDATE issue SET
                status = ?,
                updated_at = ?,
                status_changed_at = ?
            WHERE id = ?
        """
        self._db.execute(sql, (new_status, now, now, issue_id))
        self._db.commit()
        return True

    def count_by_status(self, project_id: int = None) -> dict:
        """
        统计各状态问题单数量

        Args:
            project_id: 项目ID（可选，用于项目内统计）

        Returns:
            状态统计字典 {status: count}
        """
        if project_id:
            sql = """
                SELECT status, COUNT(*) as count
                FROM issue
                WHERE project_id = ?
                GROUP BY status
            """
            data_list = self._db.fetchall(sql, (project_id,))
        else:
            sql = """
                SELECT status, COUNT(*) as count
                FROM issue
                GROUP BY status
            """
            data_list = self._db.fetchall(sql)
        return {data['status']: data['count'] for data in data_list}

    def count_all(self) -> int:
        """
        统计问题单总数

        Returns:
            问题单总数
        """
        sql = "SELECT COUNT(*) as count FROM issue"
        data = self._db.fetchone(sql)
        return data['count'] if data else 0

    def get_all_with_module_name(self) -> List[Issue]:
        """
        获取所有问题单并关联模块名称和项目名称

        Returns:
            带模块名称和项目名称的问题单列表
        """
        return self.get_all()