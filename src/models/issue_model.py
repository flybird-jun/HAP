"""
问题单数据模型

定义问题单的数据结构和状态枚举
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Optional


class IssueStatus(IntEnum):
    """
    问题单状态枚举

    状态流转：
    提交测试(0) → 开发实施修改(1) → 归档(2) → 关闭(3)
    """
    SUBMIT_TEST = 0      # 提交测试（初始状态）
    DEVELOPING = 1       # 开发实施修改
    ARCHIVED = 2         # 归档
    CLOSED = 3           # 关闭

    @classmethod
    def get_name(cls, status: int) -> str:
        """获取状态的中文名称"""
        names = {
            cls.SUBMIT_TEST: "提交测试",
            cls.DEVELOPING: "开发实施修改",
            cls.ARCHIVED: "归档",
            cls.CLOSED: "关闭"
        }
        return names.get(status, "未知状态")

    @classmethod
    def get_next(cls, current: int) -> Optional[int]:
        """获取下一个状态"""
        if current == cls.SUBMIT_TEST:
            return cls.DEVELOPING
        elif current == cls.DEVELOPING:
            return cls.ARCHIVED
        elif current == cls.ARCHIVED:
            return cls.CLOSED
        return None  # 关闭状态没有下一个状态

    @classmethod
    def get_prev(cls, current: int) -> Optional[int]:
        """获取上一个状态（用于回退）"""
        # 确保转换为整数进行比较
        current_val = int(current) if isinstance(current, IssueStatus) else current
        if current_val == cls.DEVELOPING:
            return cls.SUBMIT_TEST
        elif current_val == cls.ARCHIVED:
            return cls.DEVELOPING
        elif current_val == cls.CLOSED:
            return cls.ARCHIVED
        return None  # 提交测试状态不能回退


@dataclass
class Issue:
    """
    问题单数据模型

    字段说明：
    - id: 数据库主键
    - issue_no: 问题单号，格式 PRYYYYMMDDHHMMSS
    - title: 简要描述（纯文本）
    - description: 详细描述（富文本，支持图片路径）
    - module_id: 关联模块ID
    - project_id: 所属项目ID（必填）
    - status: 当前状态
    - root_cause: 问题原因（富文本）
    - solution: 问题修改（富文本）
    - self_test: 自测试（富文本）
    - archive_test: 归档测试描述（富文本）
    - created_at: 创建时间
    - updated_at: 更新时间
    - status_changed_at: 最后状态变更时间（用于计算停留时间）
    - module_name: 关联查询时填充的模块名称
    - project_name: 关联查询时填充的项目名称
    """
    id: Optional[int] = None
    issue_no: str = ""
    title: str = ""
    description: str = ""
    module_id: Optional[int] = None
    project_id: Optional[int] = None
    status: IssueStatus = IssueStatus.SUBMIT_TEST
    root_cause: str = ""
    solution: str = ""
    self_test: str = ""
    archive_test: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status_changed_at: Optional[datetime] = None
    module_name: str = ""  # 关联查询时填充
    project_name: str = ""  # 关联查询时填充

    def __post_init__(self):
        """初始化后处理"""
        # 确保 status 是 IssueStatus 类型
        if isinstance(self.status, int):
            self.status = IssueStatus(self.status)

    def to_dict(self) -> dict:
        """转换为字典（用于数据库操作）"""
        return {
            'id': self.id,
            'issue_no': self.issue_no,
            'title': self.title,
            'description': self.description,
            'module_id': self.module_id,
            'project_id': self.project_id,
            'status': int(self.status),
            'root_cause': self.root_cause,
            'solution': self.solution,
            'self_test': self.self_test,
            'archive_test': self.archive_test,
            'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            'updated_at': self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            'status_changed_at': self.status_changed_at.strftime("%Y-%m-%d %H:%M:%S") if self.status_changed_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Issue':
        """从字典创建实例"""
        # 处理时间字段
        created_at = None
        if data.get('created_at'):
            created_at = datetime.strptime(data['created_at'], "%Y-%m-%d %H:%M:%S")

        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.strptime(data['updated_at'], "%Y-%m-%d %H:%M:%S")

        status_changed_at = None
        if data.get('status_changed_at'):
            status_changed_at = datetime.strptime(data['status_changed_at'], "%Y-%m-%d %H:%M:%S")

        return cls(
            id=data.get('id'),
            issue_no=data.get('issue_no', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            module_id=data.get('module_id'),
            project_id=data.get('project_id'),
            status=IssueStatus(data.get('status', 0)),
            root_cause=data.get('root_cause', ''),
            solution=data.get('solution', ''),
            self_test=data.get('self_test', ''),
            archive_test=data.get('archive_test', ''),
            created_at=created_at,
            updated_at=updated_at,
            status_changed_at=status_changed_at,
            module_name=data.get('module_name', ''),
            project_name=data.get('project_name', '')
        )

    def calculate_stay_duration(self) -> str:
        """
        计算停留时间

        Returns:
            格式化的停留时间字符串，关闭状态返回 "--"
        """
        if self.status == IssueStatus.CLOSED:
            return "--"

        if not self.status_changed_at:
            return "未知"

        now = datetime.now()
        delta = now - self.status_changed_at

        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        if days > 0:
            return f"{days}天{hours}小时"
        elif hours > 0:
            return f"{hours}小时{minutes}分钟"
        else:
            return f"{minutes}分钟"

    def can_submit(self) -> bool:
        """判断是否可以提交（进入下一状态）"""
        return IssueStatus.get_next(self.status) is not None

    def can_rollback(self) -> bool:
        """判断是否可以回退（回到上一状态）"""
        return IssueStatus.get_prev(self.status) is not None

    def can_delete(self) -> bool:
        """判断是否可以删除（只有提交测试状态可删除）"""
        return self.status == IssueStatus.SUBMIT_TEST

    def validate_for_submit(self) -> tuple[bool, str]:
        """
        验证是否可以提交到下一状态

        Returns:
            (是否可以提交, 错误消息)
        """
        if self.status == IssueStatus.SUBMIT_TEST:
            # 提交测试状态不需要额外验证
            return (True, "")

        elif self.status == IssueStatus.DEVELOPING:
            # 开发实施修改状态需要填写问题原因、问题修改、自测试，选择模块
            if not self.root_cause.strip():
                return (False, "请填写问题原因")
            if not self.solution.strip():
                return (False, "请填写问题修改")
            if not self.self_test.strip():
                return (False, "请填写自测试")
            if not self.module_id:
                return (False, "请选择模块")
            return (True, "")

        elif self.status == IssueStatus.ARCHIVED:
            # 归档状态需要填写归档测试描述
            if not self.archive_test.strip():
                return (False, "请填写归档测试描述")
            return (True, "")

        else:
            return (False, "当前状态无法提交")

    @property
    def status_name(self) -> str:
        """获取状态名称"""
        return IssueStatus.get_name(self.status)