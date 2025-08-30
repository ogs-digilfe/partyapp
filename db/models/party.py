from sqlalchemy import String, Date, CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from partyapp.db.base import Base
from datetime import date

class Party(Base):
    __tablename__ = "M_PARTY"

    id: Mapped[str] = mapped_column(CHAR(18), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, doc="政党名")
    short_name: Mapped[str | None] = mapped_column(String(50))
    founded_on: Mapped[date | None] = mapped_column(Date)
    dissolved_on: Mapped[date | None] = mapped_column(Date)

    law_roles: Mapped[list["PartyLawRole"]] = relationship(
        back_populates="party", cascade="all, delete-orphan"
    )