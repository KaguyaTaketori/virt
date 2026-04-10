"""
Backward compatibility: Re-export from integrations
"""

from app.integrations.websub.subscription_service import (
    WebSubSubscriptionService,
    websub_service,
)

__all__ = ["WebSubSubscriptionService", "websub_service"]
