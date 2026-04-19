"""
项目数据模型

定义项目的数据结构
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    """
    项目数据模型

    字段说明：
    - id: 数据库主键
    - name: 项目名称（唯一）
    - description: 项目描述
    - is_default: 是否为默认项目（默认项目不可删除）
    - created_at: 创建时间
    - updated_at: 更新时间
    - module_count: 关联模块数量（查询时填充）
    - issue_count: 关联问题单数量（查询时填充）
    """
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    is_default: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    module_count: int = 0  # 查询时填充
    issue_count: int = 0   # 查询时填充

    def to_dict(self) -> dict:
        """转换为字典（用于数据库操作）"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_default': 1 if self.is_default else 0,
            'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            'updated_at': self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        """从字典创建实例"""
        created_at = None
        if data.get('created_at'):
            created_at = datetime.strptime(data['created_at'], "%Y-%m-%d %H:%M:%S")

        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.strptime(data['updated_at'], "%Y-%m-%d %H:%M:%S")

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            is_default=bool(data.get('is_default', 0)),
            created_at=created_at,
            updated_at=updated_at,
            module_count=data.get('module_count', 0),
            issue_count=data.get('issue_count', 0)
        )

    def __str__(self) -> str:
        """字符串表示"""
        return self.name

    def __repr__(self) -> str:
        """详细表示"""
        return f"Project(id={self.id}, name='{self.name}', is_default={self.is_default})"