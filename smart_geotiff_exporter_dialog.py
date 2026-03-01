# -*- coding: utf-8 -*-
"""
Smart GeoTIFF Exporter - Diálogo Principal
Interface gráfica e worker GDAL adaptados para rodar dentro do QGIS.

Autor: Clayton Igarashi <geoigarashi@gmail.com>
Versão: 1.0.0
"""

import os
import time

from qgis.PyQt.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QProgressBar,
    QGroupBox,
    QMessageBox,
    QCheckBox,
)
from qgis.PyQt.QtCore import QThread, pyqtSignal, Qt
from qgis.PyQt.QtGui import QColor

from osgeo import gdal

gdal.UseExceptions()

# ---------------------------------------------------------------------------
# Dicionários Corporativos Oficiais
# ---------------------------------------------------------------------------
PALETAS = {
    "Aptidão": {
        0: {"hex": "#CCCCCC", "name": "Sem classe (NoData)"},
        1: {"hex": "#2E7D32", "name": "Apta (0-20%)"},
        2: {"hex": "#FDD835", "name": "Restrita (20-45%)"},
        3: {"hex": "#FB8C00", "name": "Manual (45-75%)"},
        4: {"hex": "#E53935", "name": "Extrema (75-<100%)"},
        5: {"hex": "#8E24AA", "name": "APP Legal (>=100%)"},
    },
    "Declividade": {
        0: {"hex": "#CCCCCC", "name": "Sem classe (NoData/fora do raster)"},
        1: {"hex": "#2E7D32", "name": "0-3% (Plano)"},
        2: {"hex": "#66BB6A", "name": "3-8% (Suave Ondulado)"},
        3: {"hex": "#CDDC39", "name": "8-13% (Moderamente Ondulado)"},
        4: {"hex": "#FDD835", "name": "13-20% (Ondulado)"},
        5: {"hex": "#FB8C00", "name": "20-45% (Forte Ondulado)"},
        6: {"hex": "#E53935", "name": "45-75% (Montanhoso)"},
        7: {"hex": "#8E24AA", "name": "75-<100% (Escarpado)"},
        8: {"hex": "#4A148C", "name": ">=100% (APP Legal)"},
    },
    "Uso do Solo": {
        0:   {"hex": "#CCCCCC", "name": "Sem classe (NoData/fora do raster)"},
        1:   {"hex": "#c27ba0", "name": "Lavoura Anual"},
        2:   {"hex": "#9932cc", "name": "Lavoura Perene"},
        3:   {"hex": "#edde8e", "name": "Pastagem Cultivada"},
        4:   {"hex": "#d6bc74", "name": "Pastagem Nativa"},
        5:   {"hex": "#d4271e", "name": "Pastagem Degradada"},
        6:   {"hex": "#7a5900", "name": "Silvicultura (Comercial)"},
        8:   {"hex": "#1f8d49", "name": "Área de preservação (RL,APP)"},
        9:   {"hex": "#2532e4", "name": "Lagos, lagoas"},
        10:  {"hex": "#5e5e5e", "name": "Construções e Benfeitorias (+ servidão)"},
        100: {"hex": "#000000", "name": "Uso Agropecuário não Definido"},
    },
}


# ---------------------------------------------------------------------------
# THREAD DE PROCESSAMENTO GDAL (sem alterações de lógica em relação ao original)
# ---------------------------------------------------------------------------
class GdalWorker(QThread):
    progress = pyqtSignal(int)
    log      = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_path, output_path, epsg, threads, custom_palette):
        super().__init__()
        self.input_path    = input_path
        self.output_path   = output_path
        self.epsg          = epsg
        self.threads       = threads
        self.custom_palette = custom_palette

    def gdal_progress_callback(self, complete, message, user_data):
        self.progress.emit(int(complete * 100))
        return 1

    def run(self):
        try:
            start_time = time.time()
            self.log.emit(f"Iniciando leitura de: {self.input_path}")

            translate_options = gdal.TranslateOptions(
                format="GTiff",
                outputType=gdal.GDT_Byte,
                outputSRS=self.epsg,
                creationOptions=[
                    "COMPRESS=ZSTD",
                    "TILED=YES",
                    "BLOCKXSIZE=512",
                    "BLOCKYSIZE=512",
                    "BIGTIFF=YES",
                    f"NUM_THREADS={self.threads}",
                    "PREDICTOR=1",
                ],
            )

            self.log.emit("-> Executando gdal.Translate (Conversão e Compressão)...")
            ds = gdal.Translate(
                self.output_path,
                self.input_path,
                options=translate_options,
                callback=self.gdal_progress_callback,
            )

            if ds is None:
                raise Exception(
                    "Falha ao criar o arquivo de saída. "
                    "Verifique permissões ou espaço em disco."
                )

            elapsed_translate = time.time() - start_time
            self.log.emit(f"-> Conversão concluída em {elapsed_translate:.2f}s.")
            self.log.emit("-> Gerando overviews (pirâmides) via NEAREST...")
            self.progress.emit(0)

            gdal.SetConfigOption("COMPRESS_OVERVIEW", "ZSTD")
            ds.BuildOverviews(
                "NEAREST", [2, 4, 8, 16, 32, 64],
                callback=self.gdal_progress_callback
            )

            ds = None
            self.log.emit("-> Injetando Metadados Limpos (RAT Esparsa)...")

            ds_update = gdal.Open(self.output_path, gdal.GA_Update)
            band = ds_update.GetRasterBand(1)
            band.SetNoDataValue(0)

            color_table = gdal.ColorTable()
            rat = gdal.RasterAttributeTable()
            rat.CreateColumn("Value",      gdal.GFT_Integer, gdal.GFU_MinMax)
            rat.CreateColumn("Class_Name", gdal.GFT_String,  gdal.GFU_Name)
            rat.SetRowCount(len(self.custom_palette))

            for i in range(256):
                if i in self.custom_palette:
                    info = self.custom_palette[i]
                    h = info["hex"].lstrip("#")
                    rgb = tuple(int(h[j:j+2], 16) for j in (0, 2, 4)) + (255,)
                    color_table.SetColorEntry(i, rgb)
                else:
                    color_table.SetColorEntry(i, (0, 0, 0, 0))

            for row_idx, (val, info) in enumerate(self.custom_palette.items()):
                rat.SetValueAsInt(row_idx,    0, val)
                rat.SetValueAsString(row_idx, 1, info["name"])

            band.SetColorTable(color_table)
            band.SetDefaultRAT(rat)
            ds_update = None

            self.log.emit("-> Gerando arquivo de estilo rígido para QGIS (.qml)...")
            qml_path = os.path.splitext(self.output_path)[0] + ".qml"
            palette_entries = ""
            for val, info in self.custom_palette.items():
                alpha = 0 if val == 0 else 255
                label = (
                    info["name"]
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("≥", "&#8805;")
                )
                color = info["hex"]
                palette_entries += (
                    f'        <paletteEntry value="{val}" color="{color}" '
                    f'label="{label}" alpha="{alpha}"/>\n'
                )

            qml_content = f"""<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.22.0" styleCategories="Symbology">
  <pipe>
    <provider>
      <resampling zoomedInResamplingMethod="nearest" zoomedOutResamplingMethod="nearest" maxOversampling="2"/>
    </provider>
    <rasterrenderer type="paletted" opacity="1" alphaBand="-1" band="1" nodataColor="">
      <rasterTransparency/>
      <colorPalette>
{palette_entries}      </colorPalette>
    </rasterrenderer>
  </pipe>
</qgis>"""
            with open(qml_path, "w", encoding="utf-8") as f:
                f.write(qml_content)

            total_time = time.time() - start_time
            msg_final = f"Processo TOTAL concluído com sucesso em {total_time:.2f}s."
            self.log.emit(msg_final)
            self.finished.emit(True, msg_final)

        except Exception as e:
            self.log.emit(f"[ERRO CRÍTICO] {str(e)}")
            self.finished.emit(False, str(e))


# ---------------------------------------------------------------------------
# DIÁLOGO PRINCIPAL  (QDialog — substitui QMainWindow para rodar dentro do QGIS)
# ---------------------------------------------------------------------------
class SmartGeoTIFFDialog(QDialog):
    """
    Janela principal do plugin Smart GeoTIFF Exporter.
    Adaptada de QMainWindow para QDialog para integração nativa com o QGIS.
    """

    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface  = iface
        self.worker = None

        self.setWindowTitle("Smart GeoTIFF Exporter")
        self.setMinimumSize(820, 780)
        # Mantém a janela sempre visível mesmo ao clicar fora
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        self._init_ui()

    # ------------------------------------------------------------------
    # Construção da Interface
    # ------------------------------------------------------------------
    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # ── 1. Arquivos ────────────────────────────────────────────────
        group_files   = QGroupBox("Arquivos e Diretórios")
        layout_files  = QVBoxLayout()

        layout_input  = QHBoxLayout()
        self.line_input = QLineEdit()
        self.line_input.setPlaceholderText(
            "Selecione o arquivo de origem (.vrt, .sdat, .tif, .img)..."
        )
        btn_input = QPushButton("Procurar...")
        btn_input.clicked.connect(self._select_input)
        layout_input.addWidget(self.line_input)
        layout_input.addWidget(btn_input)

        # Botão de atalho: usa a camada ativa do projeto QGIS
        btn_active = QPushButton("Usar camada ativa")
        btn_active.setToolTip(
            "Preenche automaticamente com o caminho da camada raster ativa no projeto."
        )
        btn_active.clicked.connect(self._use_active_layer)
        layout_input.addWidget(btn_active)

        layout_output = QHBoxLayout()
        self.line_output = QLineEdit()
        self.line_output.setPlaceholderText(
            "Defina o destino do arquivo final (.tif)..."
        )
        btn_output = QPushButton("Salvar como...")
        btn_output.clicked.connect(self._select_output)
        layout_output.addWidget(self.line_output)
        layout_output.addWidget(btn_output)

        layout_files.addLayout(layout_input)
        layout_files.addLayout(layout_output)
        group_files.setLayout(layout_files)
        main_layout.addWidget(group_files)

        # ── 2. Parâmetros GDAL ─────────────────────────────────────────
        group_settings  = QGroupBox("Parâmetros GDAL")
        layout_settings = QHBoxLayout()

        layout_settings.addWidget(QLabel("EPSG de Saída:"))
        self.combo_epsg = QComboBox()
        self.combo_epsg.addItems(
            ["EPSG:4326", "EPSG:4674", "EPSG:31982", "EPSG:31983", "EPSG:31984"]
        )
        layout_settings.addWidget(self.combo_epsg)
        layout_settings.addSpacing(20)

        layout_settings.addWidget(QLabel("Threads:"))
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 32)
        self.spin_threads.setValue(16)
        layout_settings.addWidget(self.spin_threads)
        layout_settings.addSpacing(20)

        # Opção de carregamento automático no projeto
        self.chk_load = QCheckBox("Carregar resultado no projeto ao finalizar")
        self.chk_load.setChecked(True)
        layout_settings.addWidget(self.chk_load)

        layout_settings.addStretch()
        group_settings.setLayout(layout_settings)
        main_layout.addWidget(group_settings)

        # ── 3. Paleta e RAT ───────────────────────────────────────────
        group_palette  = QGroupBox("Metadados, Classes e Cores (RAT)")
        layout_palette = QVBoxLayout()

        layout_combo_palette = QHBoxLayout()
        layout_combo_palette.addWidget(QLabel("Tema Corporativo:"))
        self.combo_palette = QComboBox()
        self.combo_palette.addItems(list(PALETAS.keys()))
        self.combo_palette.currentTextChanged.connect(self._populate_table)
        layout_combo_palette.addWidget(self.combo_palette)
        layout_combo_palette.addStretch()
        layout_palette.addLayout(layout_combo_palette)

        self.table_palette = QTableWidget(0, 3)
        self.table_palette.setHorizontalHeaderLabels(
            ["Valor (Pixel)", "Nome da Classe", "Cor (HEX)"]
        )
        self.table_palette.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        layout_palette.addWidget(self.table_palette)

        # Botões de edição da tabela
        layout_table_btns = QHBoxLayout()

        btn_add_row = QPushButton("＋  Adicionar Classe")
        btn_add_row.setToolTip(
            "Insere uma nova linha em branco ao final da tabela para adicionar "
            "uma classe personalizada."
        )
        btn_add_row.setStyleSheet(
            "background-color: #1565C0; color: white; font-weight: bold;"
        )
        btn_add_row.clicked.connect(self._add_table_row)

        btn_remove_row = QPushButton("－  Remover Classe Selecionada")
        btn_remove_row.setToolTip(
            "Remove a(s) linha(s) selecionada(s) da tabela. "
            "Selecione uma ou mais linhas antes de clicar."
        )
        btn_remove_row.setStyleSheet(
            "background-color: #B71C1C; color: white; font-weight: bold;"
        )
        btn_remove_row.clicked.connect(self._remove_table_rows)

        btn_reset_table = QPushButton("↺  Restaurar Tema")
        btn_reset_table.setToolTip(
            "Desfaz todas as edições e restaura as classes padrão do tema selecionado."
        )
        btn_reset_table.setStyleSheet(
            "background-color: #E65100; color: white; font-weight: bold;"
        )
        btn_reset_table.clicked.connect(
            lambda: self._populate_table(self.combo_palette.currentText())
        )

        layout_table_btns.addWidget(btn_add_row)
        layout_table_btns.addWidget(btn_remove_row)
        layout_table_btns.addStretch()
        layout_table_btns.addWidget(btn_reset_table)
        layout_palette.addLayout(layout_table_btns)

        group_palette.setLayout(layout_palette)
        main_layout.addWidget(group_palette)

        # ── 4. Ações ──────────────────────────────────────────────────
        self.btn_process = QPushButton("INICIAR PROCESSAMENTO ZSTD")
        self.btn_process.setMinimumHeight(42)
        self.btn_process.setStyleSheet(
            "background-color: #2E7D32; color: white; "
            "font-weight: bold; font-size: 14px;"
        )
        self.btn_process.clicked.connect(self._start_processing)
        main_layout.addWidget(self.btn_process)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setStyleSheet(
            "background-color: #1e1e1e; color: #00ff00; font-family: Consolas;"
        )
        self.log_viewer.setMinimumHeight(150)
        main_layout.addWidget(self.log_viewer)

        # Ler versão do metadata.txt dinamicamente
        version = "1.0.0"  # fallback
        try:
            import configparser
            plugin_dir = os.path.dirname(__file__)
            metadata_path = os.path.join(plugin_dir, "metadata.txt")
            if os.path.exists(metadata_path):
                config = configparser.ConfigParser()
                config.read(metadata_path, encoding='utf-8')
                if config.has_option('general', 'version'):
                    version = config.get('general', 'version')
        except Exception:
            pass

        # Rodapé
        lbl_footer = QLabel(
            f"Smart GeoTIFF Exporter v{version}  |  Clayton Igarashi "
            "<geoigarashi@gmail.com>"
        )
        lbl_footer.setAlignment(Qt.AlignCenter)
        lbl_footer.setStyleSheet("color: gray; font-size: 10px;")
        main_layout.addWidget(lbl_footer)

        self._populate_table(self.combo_palette.currentText())

    # ------------------------------------------------------------------
    # Slots de Interface
    # ------------------------------------------------------------------
    def _select_input(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Origem", "",
            "Rasters (*.vrt *.sdat *.tif *.img);;Todos (*.*)"
        )
        if file:
            self.line_input.setText(os.path.normpath(file))

    def _select_output(self):
        file, _ = QFileDialog.getSaveFileName(
            self, "Salvar Destino", "", "GeoTIFF (*.tif)"
        )
        if file:
            self.line_output.setText(os.path.normpath(file))

    def _use_active_layer(self):
        """Preenche o campo de entrada com o caminho da camada ativa no QGIS."""
        if self.iface is None:
            QMessageBox.warning(self, "Aviso", "Interface QGIS não disponível.")
            return

        layer = self.iface.activeLayer()
        if layer is None:
            QMessageBox.warning(self, "Aviso", "Nenhuma camada ativa no projeto.")
            return

        source = layer.source()
        # Para camadas com parâmetros extras (ex: geopackage), pega só o path
        if "|" in source:
            source = source.split("|")[0]

        self.line_input.setText(os.path.normpath(source))
        self._append_log(f"Camada ativa carregada: {source}")

    def _populate_table(self, theme_name):
        self.table_palette.setRowCount(0)
        theme_data = PALETAS.get(theme_name, {})
        for row, (val, info) in enumerate(theme_data.items()):
            self.table_palette.insertRow(row)

            item_val = QTableWidgetItem(str(val))
            item_val.setFlags(item_val.flags() ^ Qt.ItemIsEditable)
            self.table_palette.setItem(row, 0, item_val)

            self.table_palette.setItem(row, 1, QTableWidgetItem(info["name"]))

            item_hex = QTableWidgetItem(info["hex"])
            # Colore a célula com a própria cor para visualização imediata
            try:
                bg = QColor(info["hex"])
                item_hex.setBackground(bg)
                # Texto preto ou branco dependendo da luminância
                lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
                item_hex.setForeground(QColor("#000000" if lum > 128 else "#FFFFFF"))
            except Exception:
                pass
            self.table_palette.setItem(row, 2, item_hex)

    def _add_table_row(self):
        """Insere uma nova linha editável ao final da tabela."""
        row = self.table_palette.rowCount()
        self.table_palette.insertRow(row)

        # Valor padrão: próximo inteiro disponível
        existing_vals = set()
        for r in range(row):
            try:
                existing_vals.add(int(self.table_palette.item(r, 0).text()))
            except Exception:
                pass
        next_val = max(existing_vals) + 1 if existing_vals else 1

        item_val = QTableWidgetItem(str(next_val))
        self.table_palette.setItem(row, 0, item_val)
        self.table_palette.setItem(row, 1, QTableWidgetItem("Nova Classe"))

        item_hex = QTableWidgetItem("#FFFFFF")
        item_hex.setBackground(QColor("#FFFFFF"))
        item_hex.setForeground(QColor("#000000"))
        self.table_palette.setItem(row, 2, item_hex)

        # Entra em modo de edição no campo Nome imediatamente
        self.table_palette.setCurrentCell(row, 1)
        self.table_palette.editItem(self.table_palette.item(row, 1))

    def _remove_table_rows(self):
        """Remove as linhas selecionadas na tabela."""
        selected_rows = sorted(
            set(idx.row() for idx in self.table_palette.selectedIndexes()),
            reverse=True  # Remove de baixo para cima para não deslocar índices
        )
        if not selected_rows:
            QMessageBox.information(
                self, "Aviso",
                "Selecione ao menos uma linha na tabela para remover."
            )
            return

        confirm = QMessageBox.question(
            self, "Confirmar Remoção",
            f"Remover {len(selected_rows)} classe(s) selecionada(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            for row in selected_rows:
                self.table_palette.removeRow(row)

    def _get_palette_from_table(self):
        custom_palette = {}
        for row in range(self.table_palette.rowCount()):
            try:
                val      = int(self.table_palette.item(row, 0).text())
                name     = self.table_palette.item(row, 1).text()
                hex_color = self.table_palette.item(row, 2).text()
                if not hex_color.startswith("#") or len(hex_color) != 7:
                    raise ValueError(f"Cor HEX inválida na linha {row + 1}")
                custom_palette[val] = {"name": name, "hex": hex_color}
            except Exception as e:
                raise Exception(f"Erro na leitura da tabela de cores: {e}")
        return custom_palette

    def _append_log(self, text):
        self.log_viewer.append(text)

    def _update_progress(self, val):
        self.progress_bar.setValue(val)

    # ------------------------------------------------------------------
    # Processamento
    # ------------------------------------------------------------------
    def _start_processing(self):
        input_file  = self.line_input.text().strip()
        output_file = self.line_output.text().strip()

        if not input_file or not output_file:
            QMessageBox.warning(
                self, "Aviso",
                "Por favor, defina os arquivos de origem e destino."
            )
            return

        try:
            custom_palette = self._get_palette_from_table()
        except Exception as e:
            QMessageBox.critical(self, "Erro de Validação", str(e))
            return

        self.btn_process.setEnabled(False)
        self.log_viewer.clear()
        self.progress_bar.setValue(0)

        self.worker = GdalWorker(
            input_file,
            output_file,
            self.combo_epsg.currentText(),
            self.spin_threads.value(),
            custom_palette,
        )
        self.worker.progress.connect(self._update_progress)
        self.worker.log.connect(self._append_log)
        self.worker.finished.connect(self._processing_finished)
        self.worker.start()

    def _processing_finished(self, success, message):
        self.btn_process.setEnabled(True)

        if success:
            QMessageBox.information(self, "Sucesso!", message)

            # Carrega automaticamente o resultado no projeto QGIS
            if self.chk_load.isChecked() and self.iface is not None:
                output_file = self.line_output.text().strip()
                layer_name  = os.path.splitext(os.path.basename(output_file))[0]
                self.iface.addRasterLayer(output_file, layer_name)
                self._append_log(
                    f"-> Camada '{layer_name}' carregada automaticamente no projeto."
                )
        else:
            QMessageBox.critical(self, "Erro no Processamento", message)
