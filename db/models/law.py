from sqlalchemy import String, Text, Date, DateTime, CHAR, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Enum as SAEnum

from partyapp.db.base import Base
from partyapp.db.models.enums import LawType, JurisdictionLevel

from datetime import datetime, date

class Law(Base):
    __tablename__ = "T_LAW"
    __table_args__ = (
        UniqueConstraint("law_number", name="uq_law_law_number"),
        Index("ix_law_created_at", "created_at"),
        Index("ix_law_updated_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(CHAR(18), primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, doc="法令名（正式名）")
    law_number: Mapped[str | None] = mapped_column(String(50), unique=True)
    type: Mapped[LawType] = mapped_column(
        SAEnum(LawType, native_enum=False, validate_strings=True), nullable=False
    )
    jurisdiction: Mapped[JurisdictionLevel] = mapped_column(
        SAEnum(JurisdictionLevel, native_enum=False, validate_strings=True), nullable=False
    )
    promulgated_on: Mapped["date | None"] = mapped_column(Date)
    enacted_on: Mapped["date | None"] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_hash: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped["datetime"] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    categories: Mapped[list["Category"]] = relationship(
        secondary="T_LAW_CATEGORY_MAP", back_populates="laws"
    )
    party_roles: Mapped[list["PartyLawRole"]] = relationship(
        back_populates="law", cascade="all, delete-orphan"
    )