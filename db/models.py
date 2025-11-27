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
    last_inactivity_message_sent = Column(DateTime, nullable=True)  # Когда последний раз отправили напоминание о неактивности

    bookings = relationship("Booking", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"))
    trainer = Column(String(50), nullable=False)
    date = Column(String(50), nullable=False)           # "15 марта 2025" (human-readable format)
    time = Column(String(5), nullable=False)            # HH:MM
    price = Column(Integer, nullable=False)
    payment_type = Column(String(20), default="single") # single / subscription
    status = Column(String(20), default="pending")      # pending, paid, done, cancelled, late_cancel
    lesson_type = Column(String(20), default="group_single")  # trial, group_single, group_subscription, individual
    created_at = Column(DateTime, default=datetime.utcnow)
    reminder_12_sent = Column(Boolean, default=False)   # 12 hours before
    reminder_2_sent = Column(Boolean, default=False)    # 2 hours before

    user = relationship("User", back_populates="bookings")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.telegram_id"))
    classes_total = Column(Integer, nullable=False)      # 4, 6 или 8 занятий
    classes_left = Column(Integer, nullable=False)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)         # purchased_at + 30 дней

    user = relationship("User", back_populates="subscriptions")
