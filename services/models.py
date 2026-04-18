from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from datetime import datetime as dt

class Base(DeclarativeBase):
    pass

class log_entry(Base):
    __tablename__ = "log_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[str] = mapped_column(String(25))
    created_at: Mapped[dt] = mapped_column(DateTime)
    updated_at: Mapped[dt] = mapped_column(DateTime)
    
    log_segments: Mapped[list["log_segment"]] = relationship(back_populates="log_entry")

class log_segment(Base):
    __tablename__ = "log_segment"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_entry_id: Mapped[int] = mapped_column(ForeignKey("log_entry.id"))
    audio_filename: Mapped[str] = mapped_column(String(255))
    audio_duration: Mapped[int] = mapped_column(Integer)
    raw_transcript: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt] = mapped_column(DateTime)
    updated_at: Mapped[dt] = mapped_column(DateTime)

    log_entry: Mapped["log_entry"] = relationship(back_populates="log_segments")

class log_enrichment(Base):
    __tablename__ = "log_enrichment"

    id: Mapped[int] = mapped_column(primary_key=True)
    log_entry_id: Mapped[int] = mapped_column(ForeignKey("log_entry.id"))
    formatted_md: Mapped[str] = mapped_column(Text)
    followup_qs: Mapped[str] = mapped_column(Text)
    weekly_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt] = mapped_column(DateTime)
    updated_at: Mapped[dt] = mapped_column(DateTime)

    log_entry: Mapped["log_entry"] = relationship(back_populates="log_enrichments")