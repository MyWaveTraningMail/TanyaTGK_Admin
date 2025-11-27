from .start import router as start_router
from .booking import router as booking_router
from .payments import router as payments_router
from .profile import router as profile_router
from .feedback import router as feedback_router
from .faq import router as faq_router
from .admin import router as admin_router

__all__ = [
    "start_router",
    "booking_router",
    "payments_router",
    "profile_router",
    "feedback_router",
    "faq_router",
    "admin_router",
]
