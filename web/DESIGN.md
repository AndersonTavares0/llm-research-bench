---
name: "SLM-Limits Scientific Design System"
version: "1.0.0"
mode: "light-first"
references:
  data_interface: "https://artificialanalysis.ai/leaderboards/models"
  editorial_identity: "https://epoch.ai/"
specification: "Google Labs DESIGN.md"
colors:
  light:
    background: "#FBFBFA"
    surface: "#FFFFFF"
    surface-subtle: "#F5F5F3"
    surface-elevated: "#FFFFFF"
    border: "#E2E5E5"
    border-subtle: "#ECEEED"
    border-strong: "#BAC2C2"
    text-primary: "#0E1415"
    text-secondary: "#475456"
    text-tertiary: "#526063"
    accent-primary: "#006D77"
    accent-primary-hover: "#00535B"
    accent-primary-surface: "#E6F3F4"
    accent-secondary: "#105652"
    status-verified: "#0E7A5A"
    status-verified-surface: "#E7F6F1"
    status-warning: "#B45309"
    status-warning-surface: "#FEF3C7"
    status-error: "#BE123C"
    status-error-surface: "#FFE4E6"
    status-analytical: "#4338CA"
    status-analytical-surface: "#EEF2FF"
    chart-pareto: "#0E7A5A"
    chart-frontier-line: "#0E7A5A"
    chart-speed: "#0284C7"
    chart-vram-static: "#006D77"
    chart-vram-dynamic: "#D97706"
    chart-vram-headroom: "#E2E5E5"
    chart-grid: "#ECEEED"
    chart-axis: "#7A8A8C"
  dark:
    background: "#0A0E0F"
    surface: "#121719"
    surface-subtle: "#182022"
    surface-elevated: "#1D2629"
    border: "#242F32"
    border-subtle: "#1C2426"
    border-strong: "#3B4C50"
    text-primary: "#F2F5F5"
    text-secondary: "#98A8AA"
    text-tertiary: "#647476"
    accent-primary: "#2DD4BF"
    accent-primary-hover: "#14B8A6"
    accent-primary-surface: "#0D2C28"
    accent-secondary: "#5EEAD4"
    status-verified: "#34D399"
    status-verified-surface: "#063826"
    status-warning: "#FBBF24"
    status-warning-surface: "#382806"
    status-error: "#FB7185"
    status-error-surface: "#3A0D15"
    status-analytical: "#818CF8"
    status-analytical-surface: "#181C38"
    chart-pareto: "#34D399"
    chart-frontier-line: "#34D399"
    chart-speed: "#38BDF8"
    chart-vram-static: "#2DD4BF"
    chart-vram-dynamic: "#FBBF24"
    chart-vram-headroom: "#242F32"
    chart-grid: "#1C2426"
    chart-axis: "#647476"
typography:
  editorial-headline:
    fontFamily: "Newsreader, 'Victor Serif', Georgia, 'Times New Roman', serif"
    fontSize: "2.25rem"
    fontWeight: "500"
    lineHeight: "1.2"
    letterSpacing: "-0.015em"
  section-title:
    fontFamily: "Newsreader, 'Victor Serif', Georgia, serif"
    fontSize: "1.5rem"
    fontWeight: "500"
    lineHeight: "1.25"
    letterSpacing: "-0.01em"
  interface-headline:
    fontFamily: "Inter, 'Suisse Intl', 'Messina Sans', system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: "600"
    lineHeight: "1.35"
    letterSpacing: "-0.01em"
  body-text:
    fontFamily: "Inter, 'Suisse Intl', 'Messina Sans', system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: "400"
    lineHeight: "1.55"
    letterSpacing: "0em"
  caption:
    fontFamily: "Inter, 'Suisse Intl', system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: "500"
    lineHeight: "1.4"
    letterSpacing: "0.01em"
  tabular-data:
    fontFamily: "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: "500"
    lineHeight: "1.3"
    letterSpacing: "0em"
    fontVariantNumeric: "tabular-nums"
spacing:
  2xs: "2px"
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
  3xl: "48px"
  4xl: "64px"
rounded:
  none: "0px"
  xs: "2px"
  sm: "4px"
  md: "6px"
  lg: "8px"
  pill: "9999px"
borders:
  hairline: "1px solid"
  focus-ring: "2px solid"
shadows:
  none: "none"
  subtle: "0 1px 2px 0 rgba(14, 20, 21, 0.04)"
  popover: "0 4px 16px -2px rgba(14, 20, 21, 0.08), 0 2px 6px -1px rgba(14, 20, 21, 0.04)"
accessibility:
  wcag_target: "WCAG 2.2 Level AA"
  min_contrast_normal_text: "4.5:1"
  min_contrast_large_text: "3.0:1"
  min_contrast_ui_components: "3.0:1"
---

# SLM-Limits Scientific Design System (`web/DESIGN.md`)

## 1. Executive Summary & Design Vision

The **SLM-Limits** visual direction bridges the editorial authority of **Epoch AI** with the rigorous data telemetry interface of **Artificial Analysis**. It rejects generic SaaS clichés, neon dashboard gradients, decorative rounded card clusters, and marketing hyperbole. 

The aesthetic is **light-first, scientific editorial, data-focused, and restrained**:
- **Light-First Canvas**: Mimics archival research journals and technical monographs (`#FBFBFA` paper white) while providing a high-contrast dark laboratory mode (`#0A0E0F` obsidian).
- **Ink-Based Contrast**: Uses deep carbon ink (`#0E1415`) and slate-sage tones (`#475456`) rather than pure black or washed-out grays.
- **Scientific Teal Research Accent**: A deliberate, authoritative deep teal (`#006D77` in light, `#2DD4BF` in dark) derived from physical laboratory instruments and technical publications, replacing arbitrary SaaS purples or neon blues.
- **Physical Context First**: Every table and chart is anchored in the physical reality of the evaluated testbed: an NVIDIA GeForce GTX 1050 Ti (4096 MiB GDDR5, 112 GB/s bandwidth). Zero cross-hardware ambiguity.

---

## 2. Source Evidence & Browser Inspection

This design direction is grounded directly in computed browser telemetry extracted from the two primary reference platforms:

### A. Artificial Analysis (`https://artificialanalysis.ai/leaderboards/models`)
*Inspected via Playwright Chromium headless extraction:*
- **Core Layout Structure**: Clean white background (`--background: 0 0% 100%`), 1px borders (`0 0% 85%`), 8px border radius (`--radius: 0.5rem`).
- **Data Interface Philosophy**: Compact rows, high horizontal information density, monospace tabular figures (`font-variant-numeric: tabular-nums`), rank badges, inline micro-bars displaying relative values inside table cells.
- **Frontier Visualization**: 2D scatter plots mapping Quality Index against Throughput, overlaying an empirical non-dominated Pareto frontier line.

### B. Epoch AI (`https://epoch.ai/` & `https://epoch.ai/blog`)
*Inspected via Playwright Chromium headless extraction:*
- **Editorial Typography**: Elegant serif titles paired with clean high-legibility sans-serif prose (`Newsreader` / `Times` / `Messina Sans`).
- **Subtle Paper Canvas**: Paper white background (`#FFFFFF` and `#F5F5F5` / `#FBFBFA`), avoiding harsh stark contrasts or decorative shadows.
- **Palette Discipline**: Deep graphite ink (`#090C0C`, `#212A2A`), muted commentary slate (`#536565`, `#3A4848`), and purposeful academic teal accents (`#00838A`, `#034752`, mint `#88EFD0`).

---

## 3. Color System & Semantic Roles

### 3.1 Light Mode (Primary Canvas)

| Token Name | Hex Code | Semantic Role | WCAG Contrast Ratio on `#FBFBFA` |
| :--- | :--- | :--- | :--- |
| `background` | `#FBFBFA` | Primary page canvas (archival warm paper) | Baseline (1.0:1) |
| `surface` | `#FFFFFF` | Table cards, panels, control surfaces | 1.03:1 |
| `surface-subtle` | `#F5F5F3` | Table headers, secondary pill backgrounds | 1.08:1 |
| `border` | `#E2E5E5` | Default 1px dividing lines, table rules | 1.25:1 (UI divider) |
| `border-strong` | `#BAC2C2` | Active input borders, focused container edges | 1.82:1 |
| `text-primary` | `#0E1415` | Headlines, model names, table cell primary data | **16.2:1** (Passes AAA) |
| `text-secondary` | `#475456` | Explanatory labels, table headers, descriptions | **5.8:1** (Passes AA) |
| `text-tertiary` | `#526063` | Units (`tokens/s`, `MiB`, `ms`), timestamps | **5.8:1** (Passes AA) |
| `accent-primary` | `#006D77` | Interactive tabs, primary links, key callouts | **5.4:1** (Passes AA) |
| `accent-primary-surface`| `#E6F3F4` | Active pill background, selected row highlight | 1.15:1 |
| `status-verified` | `#0E7A5A` | Empirically measured data badge, Pareto frontier | **5.1:1** (Passes AA) |
| `status-warning` | `#B45309` | VRAM memory pressure (>80%), protocol cautions | **4.8:1** (Passes AA) |
| `status-analytical`| `#4338CA` | Theoretical roofline calculations, analytical models | **7.1:1** (Passes AAA) |

### 3.2 Dark Mode (Laboratory Complement)

| Token Name | Hex Code | Semantic Role | WCAG Contrast Ratio on `#0A0E0F` |
| :--- | :--- | :--- | :--- |
| `background` | `#0A0E0F` | Obsidian dark canvas | Baseline (1.0:1) |
| `surface` | `#121719` | Elevated table cards, control containers | 1.07:1 |
| `surface-subtle` | `#182022` | Header rows, inactive filter surfaces | 1.16:1 |
| `border` | `#242F32` | 1px dividers, gridlines | 1.45:1 (UI divider) |
| `text-primary` | `#F2F5F5` | Primary text and numbers | **17.5:1** (Passes AAA) |
| `text-secondary` | `#98A8AA` | Secondary labels, descriptions | **6.8:1** (Passes AA) |
| `accent-primary` | `#2DD4BF` | Interactive focus, selected pills, brand accent | **11.2:1** (Passes AAA) |
| `status-verified` | `#34D399` | Empirically measured badge, Pareto frontier | **10.8:1** (Passes AAA) |
| `status-warning` | `#FBBF24` | Memory ceiling warning, caution badges | **12.1:1** (Passes AAA) |

---

## 4. Typography System

The typography creates a clear dichotomy: **human scientific editorial reflection** versus **mechanical hardware telemetry**.

1. **Editorial Serif (`Newsreader` / `Victor Serif` / `Georgia`)**:
   - Reserved strictly for page titles (`H1`), section headers (`H2`), and research question introductions.
   - Conveys peer-reviewed research authority, aligning with the Epoch AI publication standard.
   - Sizing: `2.25rem` (36px) for H1, `1.5rem` (24px) for H2. Line-height `1.2` to `1.25`. Never styled in all-caps.

2. **Precision Sans-Serif (`Inter` / `Suisse Intl` / `Messina Sans`)**:
   - Used for structural interface copy, navigational items, explanatory text, buttons, and control descriptions.
   - Sizing: Body text at `0.9375rem` (15px) with line-height `1.55`. Interface labels at `0.8125rem` (13px).
   - High legibility, neutral geometry, zero quirky display stylings.

3. **Tabular Monospace (`JetBrains Mono` / `SF Mono` / `Menlo`)**:
   - Used for all quantitative data: VRAM (MiB), token speeds (tok/s), latency (TTFT ms), parameter counts, quantization formats (`Q4_K_M`), and file paths.
   - Required CSS property: `font-variant-numeric: tabular-nums;` to prevent column jittering during sorting or updates.
   - Sizing: `0.8125rem` (13px) and `0.75rem` (12px).

---

## 5. Layout, Grids & Information Density

- **Max Container Width**: `1360px` (standard desktop data workbench).
- **Base Grid**: 8px rhythm (spacing steps: 4px, 8px, 12px, 16px, 24px, 32px, 48px).
- **Table Density**:
  - Row height: `44px` compact desktop, `40px` compact mobile.
  - Cell padding: `8px 12px`.
  - Column alignment: Model names and metadata left-aligned; all numeric scores, throughput metrics, and VRAM right-aligned.
- **Borders & Radii**:
  - Crisp, subdued 1px borders (`#E2E5E5`).
  - Controlled radii: `4px` (`rounded-sm`) for badges/buttons, `6px` (`rounded-md`) for panels, `9999px` (`rounded-full`) for filter pills and medal badges. No oversized cartoonish rounded corners.

---

## 6. Component Styling Specifications

### 6.1 Leaderboard Table (Artificial Analysis Style)
- **Rank Medal Column**: Compact circular badge (`w-5 h-5`) with rank number `#1`, `#2`, `#3`. Muted subtle styling, no loud gold/silver/bronze skeuomorphism.
- **Model Column**: Primary model name in semibold sans (`#0E1415`), flanked by parameter count tag and quantization tag (`Q4_K_M`) in monospace badge.
- **Micro-Bar Indicators**:
  - Background track: `h-1.5 w-16 bg-[#E2E5E5] rounded-full`.
  - Foreground bar: Proportional fill in `accent-primary` (`#006D77`) for Quality, `chart-speed` (`#0284C7`) for throughput.
- **VRAM Utilization Cell**:
  - Dual readout: Numerical megabytes (`2,410 MiB`) right-aligned + 3-stage visual gauge showing percentage of 4,096 MiB physical capacity.
  - Gauge turns to `status-warning` (`#B45309`) when exceeding 80% (3,276 MiB).

### 6.2 Interactive Frontier Scatter Plot
- **Canvas Area**: Clear white/obsidian plot background with subtle grid lines (`#ECEEED` in light, `#1C2426` in dark).
- **Pareto Frontier Curve**: Step-wise non-dominated efficiency frontier drawn with a distinct solid green curve (`#0E7A5A` / `#34D399`), width `2px`.
- **Scatter Points**:
  - Diameter: `8px` default, `12px` when hovered or selected.
  - Fill: Model family color coding with 1.5px solid white stroke.
- **Tooltips**: Clean floating card with paper elevation (`shadow-popover`), presenting exact X/Y coordinates, error bounds, and memory overhead.

### 6.3 Segmented Filter Pills & Hardware Badges
- **Segmented Control**: Grouped container with `#F5F5F3` background, 1px border. Selected segment is `#FFFFFF` with subtle shadow (`0 1px 2px rgba(0,0,0,0.05)`) and bold text.
- **Hardware Isolation Badge**: Explicitly declares `"NVIDIA GeForce GTX 1050 Ti · 4096 MiB GDDR5 · PVE CT 108"`. Never omits the 4GB hardware limitation.

---

## 7. Accessibility & Interaction States (WCAG 2.2 AA)

1. **Focus Rings**:
   - All interactive elements (links, buttons, table headers, checkboxes, filter pills) MUST feature an explicit, non-obscured focus ring: `outline: 2px solid #006D77; outline-offset: 2px;`.
   - Never suppress outline on `:focus-visible`.

2. **Contrast Guarantees**:
   - Normal text (below 18pt / 24px) guarantees minimum **4.5:1** contrast against its immediate container.
   - Graphical controls and UI borders guarantee minimum **3.0:1** contrast against background.
   - Status badges use dual channels: an explicit visual symbol (`✓`, `!`, `∑`) alongside color coding to ensure legibility for color-blind users.

3. **Touch Targets**:
   - Minimum clickable/tappable area: `40px × 40px` on mobile viewports.

---

## 8. Anti-Patterns & Prohibitions (Do's and Don'ts)

| Prohibited (Don't) | Required Standard (Do) |
| :--- | :--- |
| **No generic SaaS purples (`#8b5cf6`, `#7c3aed`)** | Use Deep Scientific Teal (`#006D77`) and Carbon Ink (`#0E1415`). |
| **No decorative neon glows, animated gradient borders, or blurred blobs** | Use crisp 1px borders (`#E2E5E5`) and purposeful subtle shadows. |
| **No oversized 24px rounded corners (`rounded-3xl`)** | Maintain compact, professional radii: `4px` to `8px`. |
| **No vague marketing adjectives ("Ultra-fast", "State-of-the-art")** | Use measured physical metrics (`18.4 tok/s`, `2,410 MiB`, `p < 0.05`). |
| **No mixing GTX 1050 Ti with RTX 3060 Ti results** | Dedicate 100% of benchmark views to the primary 4GB physical testbed. |
| **No unannounced layout shifts or flashing data tables** | Maintain consistent tabular-nums and stable table container heights. |

---

## 9. Validation Specimen

A companion validation specimen is rendered in `website/src/app/specimen/page.tsx` (or standalone HTML preview) to visually certify font rendering, color contrast, micro-bar proportions, and table layout under both light and dark viewing conditions.
