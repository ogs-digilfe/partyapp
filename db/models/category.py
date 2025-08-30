from sqlalchemy import String, Text, CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum
from partyapp.db.base import Base
from partyapp.db.models.enums import CategoryType

class Category(Base):
    __tablename__ = "M_CATEGORY"

    id: Mapped[str] = mapped_column(CHAR(18), primary_key=True)
    # native_enum=False により VARCHAR で保存（MySQL/MariaDBの互換性を重視）
    name: Mapped[CategoryType] = mapped_column(
        SAEnum(CategoryType, native_enum=False, validate_strings=True),
        unique=True,
        nullable=False,
        doc="分類（固定Enum）"
    )
    description: Mapped[str | None] = mapped_column(Text)

    laws: Mapped[list["Law"]] = relationship(
        secondary="T_LAW_CATEGORY_MAP", back_populates="categories"
    )