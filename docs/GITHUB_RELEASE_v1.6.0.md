# 🚀 Smart GeoTIFF Exporter — v1.6.0

**Data de Lançamento:** 22 de agosto de 2026  
**Repositório:** [smart_geotiff_exporter](https://github.com/geoigarashi/smart_geotiff_exporter)  
**Autor:** Clayton Igarashi (<geoigarashi@gmail.com>)  

---

## ✨ Destaques da Versão 1.6.0

### 🎨 Seletor Nativo de Cores e Contraste Inteligente (WCAG)
- **Abertura do `QColorDialog`:** Dê um **duplo clique** na célula de cor (coluna HEX) para abrir o seletor visual nativo de cores do sistema operacional.
- **Fundo Colorido em Tempo Real:** A célula da tabela assume imediatamente a cor escolhida ao selecionar no diálogo ou ao digitar um código hexadecimal.
- **Contraste Dinâmico:** Aplicação da fórmula de luminância da WCAG ($0.299R + 0.587G + 0.114B$) para alternar automaticamente a cor do texto entre preto e branco, garantindo 100% de legibilidade em tons claros ou escuros.

### 🔢 Ordenação *On the Fly* e Sugestão Inteligente de Classes
- **Ordenação em Tempo Real:** Ao alterar ou confirmar o valor de pixel (DN) de qualquer classe, a tabela é reordenada instantaneamente em ordem numérica crescente, mantendo a seleção e o foco na linha editada.
- **Sugestão Inteligente do Menor Valor Livre:** Ao clicar em **"Adicionar Classe"**, o plugin calcula o menor inteiro não negativo disponível (ex: se já existem 0, 1, 2 e 5, sugere automaticamente o valor **3**), aplica uma cor padrão da paleta corporativa e foca o cursor diretamente no nome da classe para agilizar o fluxo de trabalho.

### 📄 Exportação e Importação Dual de Paletas (QML e JSON)
- **Salvar Lista como `.qml` ou `.json`:** O diálogo de salvamento agora oferece suporte nativo tanto para exportar em formato estruturado **JSON** quanto para gerar diretamente um arquivo de estilo **QML do QGIS** (`rasterrenderer type="paletted"`), com escape XML seguro de caracteres especiais (`<`, `>`, `&`, `≥`).
- **Carregar Lista Universal:** O botão "Carregar Lista..." detecta automaticamente a extensão selecionada (`.qml` ou `.json`) e popula a tabela de simbologia com precisão.

---

## 🔧 Melhorias Técnicas e de Arquitetura

- ✓ **Grafo de Conhecimento (Graphify):** Sincronização completa de AST, comunidades de código e visualização interativa do grafo da versão 1.6.0.
- ✓ **Empacotamento Limpo:** Pacote ZIP de distribuição otimizado e centralizado na pasta `plugins_zip/` (1.38 MB), contendo apenas os 7 arquivos essenciais.
- ✓ **Qualidade e Conformidade PEP8:** Código 100% aderente ao linter `Ruff` e tipado com Type Hinting moderno (Python 3.12+).

---

## 📦 Instalação e Atualização

### Opção 1 — Pelo Gerenciador de Plugins do QGIS (Recomendado):
1. Abra o QGIS e acesse: **Plugins** → **Gerenciar e Instalar Plugins...**
2. Vá até a aba **Instalar a partir do ZIP**.
3. Selecione o arquivo [`smart_geotiff_exporter_v1.6.0.zip`](file:///c:/Python/QGIS%20Plugins/plugins_zip/smart_geotiff_exporter_v1.6.0.zip).
4. Clique em **Instalar plugin**.

### Opção 2 — Instalação Manual:
Extraia o conteúdo do arquivo ZIP no diretório de plugins do QGIS:
```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
```

---

## 📋 Compatibilidade

- **QGIS:** 3.16 LTS ou superior (testado até QGIS 3.34+ LTR)
- **Python:** 3.9+ / 3.12+ (compatível com GDAL nativo do QGIS)
- **SO:** Windows 10/11, Linux, macOS
