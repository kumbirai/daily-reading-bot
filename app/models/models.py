from datetime import datetime, \
    timezone

from sqlalchemy import Column, \
    DateTime, \
    ForeignKey, \
    Integer, \
    String, \
    UniqueConstraint
from sqlalchemy.orm import declarative_base, \
    relationship

Base = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class Reading(Base):
    __tablename__ = 'readings'
    id = Column(Integer,
                primary_key=True)
    reading_type = Column(String)
    date = Column(String)
    heading = Column(String)
    quote = Column(String)
    source = Column(String)
    narrative = Column(String)
    affirmation = Column(String)
    created_at = Column(DateTime,
                        default=utc_now)
    modified_at = Column(DateTime,
                         default=utc_now,
                         onupdate=utc_now)

    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('reading_type',
                         'date',
                         name='uq_reading_type_date'),
    )

    # Relationships
    recipients = relationship("Recipient",
                              back_populates="reading")


class Recipient(Base):
    __tablename__ = 'recipients'
    id = Column(Integer,
                primary_key=True)
    wa_id = Column(String)
    sent = Column(DateTime,
                  default=utc_now)
    reading_id = Column(Integer,
                        ForeignKey('readings.id'))

    # Relationships
    reading = relationship("Reading",
                           back_populates="recipients")
