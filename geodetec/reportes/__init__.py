"""Reportes PDF con formato común (ver ``plantilla.Reporte``)."""
from .plantilla import Reporte
from .registros import generar_reporte_registros

__all__ = ["Reporte", "generar_reporte_registros"]
