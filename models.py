from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    senha_hash: str
    data_criacao: str | None = None

    transactions: List["Transaction"] = Relationship(back_populates="user")

class Stock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(index=True, unique=True)
    nome: str
    preco: float
    ultima_busca: Optional[datetime] = Field(default=None)

    transactions: List["Transaction"] = Relationship(back_populates="stock")

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    ticker: str
    stock_id: int = Field(foreign_key="stock.id") 
    tipo: str  
    quantidade: float
    preco_unitario: float
    data: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="transactions")
    stock: Optional[Stock] = Relationship(back_populates="transactions")

