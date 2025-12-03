"""
Models package for custom ML model classes.

This package contains custom model class definitions that are required
for unpickling trained models.
"""

from app.models.ultra_ensemble import UltraEnsembleModel

__all__ = ['UltraEnsembleModel']
