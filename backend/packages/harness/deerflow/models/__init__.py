# [DL-INSIGHT] Single exported symbol: all provider, credential, and patch complexity is hidden behind create_chat_model.
# Callers never import providers directly — the factory is the entire public contract of this package.
from .factory import create_chat_model

__all__ = ["create_chat_model"]
