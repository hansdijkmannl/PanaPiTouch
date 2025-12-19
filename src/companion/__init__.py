"""
Companion Integration Module

Provides integration with Bitfocus Companion for Stream Deck control.
"""
from .companion_api import (
    CompanionAPI,
    CompanionButton,
    CompanionControlMode,
    HybridCameraControl
)

__all__ = [
    'CompanionAPI',
    'CompanionButton',
    'CompanionControlMode',
    'HybridCameraControl',
]
