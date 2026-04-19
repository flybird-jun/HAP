"""
模块数据模型

定义模块的数据结构
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Module:
    """
    模块数据模型

    字段说明：
    - id: 数据库主键
    - name: 模块名称（项目内唯一）
    - project_id: 所属项目ID
    - created_at: 创建时间
    - issue_count: 关联的问题单数量（查询时填充）
    - project_name: 所属项目名称（查询时填充）
    """
    id: Optional[int] = None
    name: str = ""
    project_id: Optional[int] = None
    created_at: Optional[datetime] = None
    issue_count: int = 0  # 查询时填充
    project_name: str = ""  # 查询时填充

    def to_dict(self) -> dict:
        """转换为字典（用于数据库操作）"""
        return {
            'id': self.id,
            'name': self.name,
            'project_id': self.project_id,
            'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Module':
        """从字典创建实例"""
        created_at = None
        if data.get('created_at'):
            created_at = datetime.strptime(data['created_at'], "%Y-%m-%d %H:%M:%S")

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            project_id=data.get('project_id'),
            created_at=created_at,
            issue_count=data.get('issue_count', 0),
            project_name=data.get('project_name', '')
        )

    def __str__(self) -> str:
        """字符串表示"""
        return self.name

    def __repr__(self) -> str:
        """详细表示"""
        return f"Module(id={self.id}, name='{self.name}')"