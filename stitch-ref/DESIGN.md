---
name: PolarisLex
colors:
  surface: '#0e141c'
  surface-dim: '#0e141c'
  surface-bright: '#343943'
  surface-container-lowest: '#090e17'
  surface-container-low: '#171c24'
  surface-container: '#1b2029'
  surface-container-high: '#252a33'
  surface-container-highest: '#30353e'
  on-surface: '#dee2ef'
  on-surface-variant: '#c2c6d6'
  inverse-surface: '#dee2ef'
  inverse-on-surface: '#2c313a'
  outline: '#8c909f'
  outline-variant: '#424754'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e6a'
  primary-container: '#4d8eff'
  on-primary-container: '#00285d'
  inverse-primary: '#005ac2'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#ffb786'
  on-tertiary: '#502400'
  tertiary-container: '#df7412'
  on-tertiary-container: '#461f00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#004395'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb786'
  on-tertiary-fixed: '#311400'
  on-tertiary-fixed-variant: '#723600'
  background: '#0e141c'
  on-background: '#dee2ef'
  surface-variant: '#30353e'
typography:
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
  code-snippet:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  gutter: 16px
  sidebar-width: 260px
---

## Brand & Style
The design system is engineered for deep analytical focus, catering to legal professionals and researchers navigating complex data relationships. The personality is "Academic Technical"—combining the rigor of a scientific tool with the precision of a developer environment.

The visual style is **Corporate / Modern** with a strong influence from **Developer Tools**. It prioritizes information density over white space and utility over ornamentation. The interface uses a "High-Precision" aesthetic characterized by thin lines, structured grids, and a strict dark-mode color logic that reduces eye strain during prolonged research sessions.

## Colors
This design system utilizes a "Deep Tech" dark palette. The background hierarchy relies on slight shifts in value rather than shadows to define depth.

- **Primary Blue:** Used for active states, primary actions, and confirmed legal citations.
- **Surface & Border:** Surfaces are tightly bound by subtle blue-gray borders (#1f242d) to create clear compartmentalization of data without visual clutter.
- **Semantic Accents:** Colors like Emerald and Amber are used sparingly for legal "Matches" and "Conflicts," ensuring they stand out against the muted navy background.
- **Neutrality:** Text levels are strictly tiered to ensure metadata (secondary text) does not compete with primary case law or research findings.

## Typography
The typography system uses a dual-font approach to separate content from metadata.

1.  **UI & Content:** *Hanken Grotesk* provides a sharp, contemporary sans-serif feel for all readability-focused elements like case summaries and navigation.
2.  **Metadata & Data:** *JetBrains Mono* is used for all "technical" data points: IDs, section numbers, relationship types (e.g., `CITES_BY`), and timestamps. This font choice signals to the user that the information is a discrete data attribute.

All labels and technical metadata should use `uppercase` or `tabular-nums` where appropriate to maintain the professional, console-like feel.

## Layout & Spacing
The layout follows a **Fluid Grid** model with high density. 

- **Grid:** A 12-column system is used for dashboard views, while research document views use a centered column with fixed-width sidebars for metadata analysis.
- **Density:** Spacing is compact. A base unit of 4px allows for tight alignment of technical panels.
- **Sidebars:** Persistent left navigation for system-level switching, with an optional right-side "Inspector" panel for viewing specific node details or citation metadata.
- **Margins:** External page margins are 24px on desktop to maximize the horizontal space for data tables and graph visualizations.

## Elevation & Depth
This system avoids traditional shadows to maintain a "flat technical" look. Depth is communicated through **Tonal Layers** and **Borders**:

- **Level 0 (Base):** Background (#0a0c10) for the main canvas or page structure.
- **Level 1 (Surface):** Surface (#11141b) for cards, panels, and sidebars.
- **Level 2 (Interaction):** Subtle hover states use #1f242d. 
- **Separation:** All panels must have a 1px solid border (#1f242d). Shadows are only used for floating menus or tooltips, using a sharp, low-spread dark shadow with 0% blur to mimic a "stacked" physical layer.

## Shapes
The shape language is rigid and precise. 

- **Corner Radius:** A universal 4px radius (`roundedness: 1`) is applied to buttons, input fields, and panels. This provides a subtle nod to modern software without losing the "industrial" feel.
- **Tags/Badges:** Monospace badges use a 2px radius or remain completely sharp to distinguish them from interactive buttons.
- **Graph Nodes:** Relationship graph nodes should be circles or hexagons to contrast against the rectangular UI elements.

## Components
- **Buttons:** Primary buttons use a solid blue background with white text. Secondary buttons are outlined with #1f242d. Text is always centered and uses `label-md` for a technical feel.
- **Data Tables:** Headers use `label-sm` with a background tint of #1f242d. Rows use a 1px bottom border only. Hovering over a row should highlight it in #11141b.
- **Input Fields:** Background is the same as the base level (#0a0c10) to create a "punched-in" effect. Borders brighten to the primary color on focus.
- **Technical Metrics:** Small cards containing a label (Monospace, Secondary Text) and a value (Large Sans-Serif, Primary Text). Often includes a small sparkline or status indicator.
- **Monospace Badges:** Small rectangular chips with a background tint corresponding to the semantic color (e.g., 10% opacity Emerald for "Match").
- **Graph Canvas:** The background should feature a subtle 16px dot grid. Relationship lines should be thin (1px) with directional arrows.