from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean,
    ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    full_name = Column(String(100))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"))
    trainer = Column(String(50), nullable=False)
    date = Column(String(10), nullable=False)           # YYYY-MM-DD
    time = Column(String(5), nullable=False)            # HH:MM
    price = Column(Integer, nullable=False)
    payment_type = Column(String(20), default="single") # single / subscription
    status = Column(String(20), default="pending")      # pending, paid, done, cancelled, noshow
    created_at = Column(DateTime, default=datetime.utcnow)
    reminder_24_sent = Column(Boolean, default=False)
    reminder_2_sent = Column(Boolean, default=False)

    user = relationship("User", back_populates="bookings")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"))
    classes_total = Column(Integer, nullable=False)      # 5 или 10
    classes_left = Column(Integer, nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="subscriptions")
