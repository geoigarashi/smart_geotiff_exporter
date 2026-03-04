# -*- coding: utf-8 -*-
"""
Smart GeoTIFF Exporter - Plugin QGIS
Ponto de entrada obrigatório para o gerenciador de plugins do QGIS.
"""


def classFactory(iface):
    """Carrega a classe principal do plugin.

    :param iface: Interface QGIS (QgisInterface)
    """
    from .smart_geotiff_exporter import SmartGeoTIFFExporter

    return SmartGeoTIFFExporter(iface)
