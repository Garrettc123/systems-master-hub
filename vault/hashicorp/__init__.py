"""Garcar HashiCorp Vault integration package."""
from .client import GarcarVault, build_from_env

__all__ = ["GarcarVault", "build_from_env"]
