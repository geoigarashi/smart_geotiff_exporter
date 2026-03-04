# -*- coding: utf-8 -*-
"""
Smart GeoTIFF Exporter
Classe principal do plugin: registra o menu, toolbar e ação no QGIS.

Autor: Clayton Igarashi <geoigarashi@gmail.com>
Versão: 1.0.0
"""

import os
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction


class SmartGeoTIFFExporter:
    """Classe principal do plugin QGIS."""

    def __init__(self, iface):
        """
        :param iface: Instância da interface QGIS (QgisInterface).
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None

    def initGui(self):
        """Inicializa a interface do plugin: cria menu e botão na toolbar."""
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon, "Smart GeoTIFF Exporter", self.iface.mainWindow())
        self.action.setToolTip(
            "Exporta rasters para GeoTIFF otimizado com ZSTD, pirâmides, "
            "paleta corporativa e QML automático."
        )
        self.action.triggered.connect(self.run)

        # Adiciona ao menu Raster do QGIS
        self.iface.addPluginToRasterMenu("Smart GeoTIFF Exporter", self.action)

        # Adiciona botão na toolbar de plugins
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        """Remove o plugin do menu e da toolbar ao desativar."""
        self.iface.removePluginRasterMenu("Smart GeoTIFF Exporter", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Abre o diálogo principal do plugin."""
        from .smart_geotiff_exporter_dialog import SmartGeoTIFFDialog

        # Reutiliza a instância do diálogo se já existir
        if self.dialog is None:
            self.dialog = SmartGeoTIFFDialog(
                iface=self.iface, parent=self.iface.mainWindow()
            )

        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
