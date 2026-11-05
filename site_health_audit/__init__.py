"""site-health-audit: one-request homepage health & tech audit for lead lists.
Built and maintained by ProfitMaker, an AI agent operated for Avatar 8 LLC."""
from .audit import audit, detect_tech
__version__ = "0.1.0"
__all__ = ["audit", "detect_tech", "__version__"]
