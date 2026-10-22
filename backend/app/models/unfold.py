from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import String, Text, DateTime, JSON, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class UnfoldJobStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class UnfoldJob(Base):
    __tablename__ = "unfold_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id"), nullable=False, index=True)
    k_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    bend_table: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    kerf: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[UnfoldJobStatus] = mapped_column(default=UnfoldJobStatus.PENDING, nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_id: Mapped[int | None] = mapped_column(ForeignKey("unfold_results.id"), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    part: Mapped["Part"] = relationship("Part", back_populates="unfold_jobs")
    result: Mapped["UnfoldResult"] = relationship("UnfoldResult", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<UnfoldJob(id={self.id}, part_id={self.part_id}, status={self.status})>"


class UnfoldResult(Base):
    __tablename__ = "unfold_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("unfold_jobs.id"), nullable=False, unique=True, index=True)
    profile_path: Mapped[str] = mapped_column(String(500), nullable=False)
    bend_lines_path: Mapped[str] = mapped_column(String(500), nullable=False)
    blank_area: Mapped[float] = mapped_column(Float, nullable=False)
    volume_conservation_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    bend_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    job: Mapped["UnfoldJob"] = relationship("UnfoldJob", back_populates="result")
    bends: Mapped[list["BendRecord"]] = relationship("BendRecord", back_populates="result", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<UnfoldResult(id={self.id}, job_id={self.job_id}, bends={self.bend_count})>"


class BendRecord(Base):
    __tablename__ = "bend_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("unfold_results.id"), nullable=False, index=True)
    bend_index: Mapped[int] = mapped_column(Integer, nullable=False)
    angle_degrees: Mapped[float] = mapped_column(Float, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "up" or "down"
    inside_radius: Mapped[float] = mapped_column(Float, nullable=False)
    bend_allowance: Mapped[float] = mapped_column(Float, nullable=False)
    flange_length_side_a: Mapped[float] = mapped_column(Float, nullable=False)
    flange_length_side_b: Mapped[float] = mapped_column(Float, nullable=False)
    nearest_cut_distance: Mapped[float] = mapped_column(Float, nullable=False)
    bend_line_start: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"x": float, "y": float}
    bend_line_end: Mapped[dict] = mapped_column(JSON, nullable=False)
    metadata_: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    result: Mapped["UnfoldResult"] = relationship("UnfoldResult", back_populates="bends")

    def __repr__(self) -> str:
        return f"<BendRecord(id={self.id}, angle={self.angle_degrees}, radius={self.inside_radius})>"