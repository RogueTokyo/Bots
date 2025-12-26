from typing import Any
from sqlalchemy import Column, Integer, String, Boolean, Index
from bot.utils.database import Base

class Shop(Base):
    """
    Модель магазина с полями:
    - id: уникальный идентификатор
    - user_id: идентификатор пользователя-владельца
    - name: название магазина
    - client_id: идентификатор клиента в API
    - api_key: ключ для доступа к API
    - is_active: статус активности магазина
    """
    __tablename__ = "shops"

    id: int = Column(Integer, primary_key=True, index=True)
    user_id: int = Column(Integer, nullable=False, index=True)
    name: str = Column(String(255), nullable=False)
    client_id: str = Column(String(255), nullable=False)
    api_key: str = Column(String(500), nullable=False)
    is_active: bool = Column(Boolean, default=True, nullable=False)

    # Индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_user_active', 'user_id', 'is_active'),
        Index('idx_client_id', 'client_id'),
    )

    def __repr__(self) -> str:
        return f"<Shop(id={self.id}, name='{self.name}', user_id={self.user_id}, is_active={self.is_active})>"
