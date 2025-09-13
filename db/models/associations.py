from sqlalchemy import CHAR, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SAEnum

from partyapp.db.base import Base
from partyapp.db.models.enums import PartyRole

# 多対多（Law - Category）単純アソシエーション
class LawCategoryMap(Base):
    __tablename__ = "T_LAW_CATEGORY_MAP"

    # 合成PK
    law_id: Mapped[str] = mapped_column(CHAR(18), ForeignKey("T_LAW.id"), primary_key=True)
    category_id: Mapped[str] = mapped_column(CHAR(18), ForeignKey("M_CATEGORY.id"), primary_key=True)

    __table_args__ = (
        Index("ix_lcm_category_id", "category_id"),
    )

# Law と Party の間のアソシエーション（追加属性 role, note 付き）
class PartyLawRole(Base):
    __tablename__ = "T_PARTY_LAW_ROLE"

    law_id: Mapped[str] = mapped_column(CHAR(18), ForeignKey("T_LAW.id"), primary_key=True)
    party_id: Mapped[str] = mapped_column(CHAR(18), ForeignKey("M_PARTY.id"), primary_key=True)
    role: Mapped[PartyRole] = mapped_column(
        SAEnum(PartyRole, native_enum=False, validate_strings=True), primary_key=True
    )
    note: Mapped[str | None] = mapped_column(Text)

    law: Mapped["Law"] = relationship(back_populates="party_roles")
    party: Mapped["Party"] = relationship(back_populates="law_roles")

    __table_args__ = (
        Index("ix_plr_party_id", "party_id"),
        Index("ix_plr_role", "role"),
    )