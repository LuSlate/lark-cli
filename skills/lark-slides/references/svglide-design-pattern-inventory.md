# SVGlide Design Pattern Inventory

This file describes internal SVGlide design patterns used by the SVG generation pipeline.
The CLI must not read an external slide-generation project at runtime; all usable patterns here are abstracted into SVGlide-owned ids, contracts, and renderer inputs.

## Policy

- Runtime dependency: none.
- Source SVG/PPTX assets are not copied into output.
- Patterns represent page rhythm, layout archetypes, chart geometry, style cues, image composition, and review heuristics.
- Production use still requires a normalized SVGlide renderer, clear asset/license status, and quality gate evidence.

## Counts

- `brand_preset`: 2
- `chart_template`: 71
- `deck_template`: 8
- `example_media_files`: 259
- `example_pages`: 356
- `example_project`: 21
- `icon_library`: 5
- `icon_svg_files`: 11631
- `image_palette`: 14
- `image_reference_collection`: 3
- `image_rendering`: 20
- `image_type_template`: 11
- `layout_template`: 7
- `narrative_mode`: 5
- `total_resources`: 191
- `visual_style`: 18
- `workflow_reference`: 6

## Pattern Kinds

- `brand_preset`: `brand.anthropic`, `brand.google`
- `chart_template`: `chart.agenda_list`, `chart.arc_anchored_list`, `chart.area_chart`, `chart.bar_chart`, `chart.basic_table`, `chart.box_plot_chart`, `chart.bubble_chart`, `chart.bullet_chart` (+63)
- `deck_template`: `deck.中国电信`, `deck.中国电建_常规`, `deck.中国电建_现代`, `deck.中汽研_商务`, `deck.中汽研_常规`, `deck.中汽研_现代`, `deck.招商银行`, `deck.重庆大学`
- `example_project`: `example.svglide_16x9_attention_is_all_you_need`, `example.svglide_16x9_brutalist_ai_newspaper_2026`, `example.svglide_16x9_building_effective_agents`, `example.svglide_16x9_cangzhuo`, `example.svglide_16x9_fashion_weekly_digest`, `example.svglide_16x9_general_dark_tech_claude_code_auto_mode`, `example.svglide_16x9_glassmorphism_demo`, `example.svglide_16x9_editorial_ai_capital_2026` (+13)
- `icon_library`: `icon_library.chunk-filled`, `icon_library.phosphor-duotone`, `icon_library.simple-icons`, `icon_library.tabler-filled`, `icon_library.tabler-outline`
- `image_palette`: `image_palette.cool-corporate`, `image_palette.dark-cinematic`, `image_palette.duotone`, `image_palette.earthy-dusty`, `image_palette.editorial-classic`, `image_palette.frost-ice`, `image_palette.jewel-tone`, `image_palette.macaron` (+6)
- `image_reference_collection`: `image_reference_collection.palette`, `image_reference_collection.rendering`, `image_reference_collection.type`
- `image_rendering`: `image_rendering.3d-isometric`, `image_rendering.blueprint`, `image_rendering.chalkboard`, `image_rendering.corporate-photo`, `image_rendering.digital-dashboard`, `image_rendering.editorial`, `image_rendering.fantasy-animation`, `image_rendering.flat` (+12)
- `image_type_template`: `image_type.comparison`, `image_type.cycle`, `image_type.flowchart`, `image_type.framework`, `image_type.funnel`, `image_type.infographic`, `image_type.map`, `image_type.matrix` (+3)
- `layout_template`: `layout.academic_defense`, `layout.ai_ops`, `layout.government_blue`, `layout.government_red`, `layout.medical_university`, `layout.pixel_retro`, `layout.psychology_attachment`
- `narrative_mode`: `mode.briefing`, `mode.instructional`, `mode.narrative`, `mode.pyramid`, `mode.showcase`
- `visual_style`: `visual_style.blueprint`, `visual_style.brutalist`, `visual_style.chalkboard`, `visual_style.dark-tech`, `visual_style.data-journalism`, `visual_style.editorial`, `visual_style.glassmorphism`, `visual_style.ink-notes` (+10)
- `workflow_reference`: `workflow.executor-base`, `workflow.image-layout-patterns`, `workflow.image-layout-spec`, `workflow.shared-standards`, `workflow.strategist`, `workflow.visual-review`

## Runtime Contract

- Select patterns through `design_pattern_selection.selected_assets`.
- Prove emitted usage through `receipts/design-pattern-usage.json`.
- Store page-level evidence in `page_usages[].component_ids` and `source_trace`.
