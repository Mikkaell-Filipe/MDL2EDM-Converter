# FSX / P3D / MSFS `.mdl` → Blender → DCS (`io_scene_mdl`)

![Version](https://img.shields.io/badge/Version-0.1.0--alpha-blue?style=flat-square)
![Blender](https://img.shields.io/badge/Blender-4.2%2B%20%7C%205.x-F5792A?style=flat-square&logo=blender&logoColor=white)
![Source Formats](https://img.shields.io/badge/Input-FSX%20%7C%20P3D%20%7C%20MSFS%20(.mdl)-0078D4?style=flat-square)
![DCS World](https://img.shields.io/badge/Target-DCS%20World%20EDM-1F2937?style=flat-square)

**Language / Idioma:** [English](#english) | [Português](#português)

---

## English

Blender add-on (`v0.1.0`) for importing **FSX, Prepar3D (P3D), and MSFS `.mdl`** aircraft/cockpit models and preparing their hierarchy, meshes, and animation pivots for **DCS World** export alongside **`io_scene_edm_custom`**.

> **Status & Limitations (`v0.1.0-alpha`):**  
> - **Not yet tested** live inside Blender or in-engine inside DCS World.  
> - **Visibility expressions (`mdl_visible_expr`)** are imported strictly as text metadata and are **not** automatically converted into `ArgVisibilityNode` entries.

### Installation

1. Make sure **`io_scene_edm_custom`** is also installed and enabled (used for patching/exporting the resulting scene to `.edm`).
2. Go to the **[Releases](../../releases/latest)** tab and download **`io_scene_mdl.zip`** *(do not extract the `.zip` file)*.
3. In **Blender**, open **Edit > Preferences > Add-ons**.
4. Click the drop-down arrow (`v`) in the top-right corner and select **Install from Disk...**.
5. Select `io_scene_mdl.zip` and enable the add-on.

### Workflow

1. **Import `.mdl`:**  
   Go to **File > Import > `MDL FSX/P3D/MSFS (.mdl) -> DCS`**.
2. **Generated Scene Structure:**  
   The importer automatically creates:
   - **1 mesh** per `PART`
   - **1 empty** per hierarchy node
   - **1 animation pivot** (`edm_new_anim`) per animated node, keyed using the official DCS frame convention:
     $$\text{frame} = (\text{arg} + 1) \times 100$$
3. **Remap DCS Arguments:**  
   Open Blender's **Text Editor** and inspect **`MDL_Import_Report`**. It contains a lookup table mapping each sequential placeholder argument to the original simulator variable. Replace the `edm_anim_arg` custom property on each pivot with the actual target DCS argument number.
4. **Fix Inverted Rotations *(if needed)*:**  
   If imported parts rotate in the opposite direction, re-import the `.mdl` with the **"Inverter sentido das rotacoes"** (*Invert rotation direction*) option enabled.
5. **Export to DCS:**  
   Use **`io_scene_edm_custom`** to patch/export the prepared geometry and `edm_new_anim` pivots into your target `.edm` file.

---

## Português

Add-on para Blender (`v0.1.0`) destinado a importar modelos **`.mdl` do FSX, Prepar3D (P3D) e MSFS**, estruturando hierarquia, malhas e pivôs de animação prontos para exportação ao **DCS World** em conjunto com o **`io_scene_edm_custom`**.

> **Status e Limitações (`v0.1.0-alpha`):**  
> - **Ainda não testado** dentro do Blender nem dentro do DCS World.  
> - **Regras de visibilidade (`mdl_visible_expr`)** são preservadas apenas como texto e **não** são convertidas automaticamente em `ArgVisibilityNode`.

### Instalação

1. Certifique-se de que o add-on **`io_scene_edm_custom`** também esteja instalado e ativado (necessário para exportar/aplicar patch no `.edm` final).
2. Acesse a aba **[Releases](../../releases/latest)** e baixe o arquivo **`io_scene_mdl.zip`** *(não extraia o `.zip`)*.
3. No **Blender**, abra **Edit > Preferences > Add-ons**.
4. Clique na seta no canto superior direito (`v`) e selecione **Install from Disk...**.
5. Selecione `io_scene_mdl.zip` e ative o add-on.

### Fluxo de Trabalho

1. **Importar `.mdl`:**  
   Vá em **File > Import > `MDL FSX/P3D/MSFS (.mdl) -> DCS`**.
2. **Estrutura Gerada na Cena:**  
   O importador cria automaticamente:
   - **1 mesh** por `PART`
   - **1 empty** por nó da hierarquia
   - **1 pivô de animação** (`edm_new_anim`) por nó animado, seguindo a convenção oficial de frames do DCS:
     $$\text{frame} = (\text{arg} + 1) \times 100$$
3. **Substituir os Argumentos do DCS:**  
   Abra o **Text Editor** do Blender e consulte o relatório **`MDL_Import_Report`**, que exibe a tabela relacionando cada argumento sequencial provisório à variável original do simulador. Altere a propriedade `edm_anim_arg` de cada pivô para o número de argumento real do seu módulo no DCS.
4. **Corrigir Rotações Invertidas *(se necessário)*:**  
   Caso as peças girem no sentido contrário, reimporte o arquivo marcando a opção **"Inverter sentido das rotacoes"**.
5. **Exportar para o DCS:**  
   Utilize o **`io_scene_edm_custom`** para gravar a geometria e os pivôs `edm_new_anim` no arquivo `.edm` de destino.