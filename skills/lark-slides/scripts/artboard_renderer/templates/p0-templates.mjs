import { Badge, Chip, StatCard, Subtitle, TextBlock, Title, box } from '../components/primitives.mjs'

const CANVAS = { width: 960, height: 540 }
const DEFAULT_FONT_FAMILY = 'SVGlideDefault'

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    background: source.background || '#0F172A',
    panel: source.panel || '#111827',
    primary: source.primary || '#38BDF8',
    accent: source.accent || '#A78BFA',
    text: source.text || '#F8FAFC',
    muted: source.muted || '#CBD5E1'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function list(spec, key) {
  const value = spec.content?.[key]
  return Array.isArray(value) ? value.filter((item) => typeof item === 'string' && item.trim()).map((item) => item.trim()) : []
}

function firstList(spec, keys, fallback = []) {
  for (const key of keys) {
    const values = list(spec, key)
    if (values.length) return values
  }
  return fallback
}

function themeSize(spec, key, fallback) {
  const value = spec.theme?.typography?.[key]
  return typeof value === 'number' ? value : fallback
}

function pageShell(spec, children) {
  const theme = colors(spec)
  return box(
    {
      width: CANVAS.width,
      height: CANVAS.height,
      position: 'relative',
      flexDirection: 'column',
      backgroundColor: theme.background,
      color: theme.text,
      fontFamily: DEFAULT_FONT_FAMILY,
      padding: 56
    },
    children
  )
}

function pageHeader(spec, { titleWidth = 720, titleSize = null, subtitleKey = 'subtitle' } = {}) {
  const theme = colors(spec)
  return box({ flexDirection: 'column', marginBottom: 28 }, [
    Badge(text(spec, 'eyebrow', '').toUpperCase(), {
      color: theme.primary,
      fontSize: 16,
      fontWeight: 800,
      marginBottom: 12
    }),
    Title(text(spec, 'title', 'Untitled'), {
      width: titleWidth,
      color: theme.text,
      fontSize: titleSize || themeSize(spec, 'title', 42),
      fontWeight: 850,
      lineHeight: 1.08,
      marginBottom: 14
    }),
    Subtitle(text(spec, subtitleKey, ''), {
      width: Math.min(titleWidth, 700),
      color: theme.muted,
      fontSize: themeSize(spec, 'subtitle', 21),
      lineHeight: 1.22
    })
  ])
}

function numberedRows(items, theme, { start = 1, max = 6 } = {}) {
  return items.slice(0, max).map((item, index) =>
    box(
      {
        width: '100%',
        minHeight: 46,
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
        backgroundColor: theme.panel,
        padding: '11px 14px'
      },
      [
        TextBlock(String(index + start).padStart(2, '0'), {
          width: 48,
          color: theme.primary,
          fontSize: 18,
          fontWeight: 850
        }),
        TextBlock(item, {
          flex: 1,
          color: theme.text,
          fontSize: 20,
          fontWeight: 650,
          lineHeight: 1.15
        })
      ]
    )
  )
}

function smallCard(label, value, theme, style = {}) {
  return box(
    {
      width: 184,
      minHeight: 112,
      flexDirection: 'column',
      backgroundColor: theme.panel,
      padding: 18,
      ...style
    },
    [
      TextBlock(label, { color: theme.muted, fontSize: 15, fontWeight: 700, marginBottom: 14 }),
      TextBlock(value, { color: theme.text, fontSize: 25, fontWeight: 850, lineHeight: 1.05 })
    ]
  )
}

function coverHero(spec) {
  const theme = colors(spec)
  const chips = list(spec, 'chips').slice(0, 4)
  return box(
    {
      width: CANVAS.width,
      height: CANVAS.height,
      position: 'relative',
      flexDirection: 'column',
      backgroundColor: theme.background,
      color: theme.text,
      fontFamily: DEFAULT_FONT_FAMILY,
      padding: 72
    },
    [
      box({
        position: 'absolute',
        left: 724,
        top: 36,
        width: 192,
        height: 192,
        borderRadius: 96,
        backgroundColor: theme.accent,
        opacity: 0.28
      }),
      box({
        width: 704,
        minHeight: 356,
        flexDirection: 'column',
        backgroundColor: theme.panel,
        opacity: 0.96,
        padding: 28
      }, [
        Badge(text(spec, 'eyebrow', 'SVGLIDE ARTBOARD'), {
          color: theme.primary,
          marginBottom: 18
        }),
        Title(text(spec, 'title', 'Untitled'), {
          color: theme.text,
          fontSize: 58,
          fontWeight: 800,
          lineHeight: 1.05,
          marginBottom: 20
        }),
        Subtitle(text(spec, 'subtitle', ''), {
          color: theme.muted,
          fontSize: 24,
          fontWeight: 500,
          lineHeight: 1.25
        })
      ]),
      box(
        {
          position: 'absolute',
          left: 84,
          top: 444,
          flexDirection: 'row',
          gap: 14
        },
        chips.map((chip) =>
          Chip(chip, {
            backgroundColor: theme.primary,
            color: theme.text,
            opacity: 0.86
          })
        )
      )
    ]
  )
}

function comparisonCards(spec) {
  const theme = colors(spec)
  const leftPoints = list(spec, 'left_points').slice(0, 3)
  const rightPoints = list(spec, 'right_points').slice(0, 3)
  const point = (value, color) =>
    box({ flexDirection: 'row', alignItems: 'center', marginBottom: 18 }, [
      box({ width: 10, height: 10, borderRadius: 5, backgroundColor: color, marginRight: 14 }),
      TextBlock(value, { color: theme.muted, fontSize: 20, fontWeight: 500, lineHeight: 1.2 })
    ])
  return box(
    {
      width: CANVAS.width,
      height: CANVAS.height,
      position: 'relative',
      flexDirection: 'column',
      backgroundColor: theme.background,
      color: theme.text,
      fontFamily: DEFAULT_FONT_FAMILY,
      padding: '52px 64px'
    },
    [
      Title(text(spec, 'title', 'Comparison'), { color: theme.text, fontSize: 40, lineHeight: 1.1, marginBottom: 44 }),
      box({ flexDirection: 'row', gap: 52 }, [
        box({ width: 390, height: 250, flexDirection: 'column', backgroundColor: theme.panel, padding: 28 }, [
          Title(text(spec, 'left_title', 'Before'), { color: theme.primary, fontSize: 24, lineHeight: 1.1, marginBottom: 28 }),
          ...leftPoints.map((item) => point(item, theme.primary))
        ]),
        box({ width: 390, height: 250, flexDirection: 'column', backgroundColor: theme.panel, padding: 28 }, [
          Title(text(spec, 'right_title', 'After'), { color: theme.accent, fontSize: 24, lineHeight: 1.1, marginBottom: 28 }),
          ...rightPoints.map((item) => point(item, theme.accent))
        ])
      ]),
      TextBlock(text(spec, 'conclusion', ''), {
        position: 'absolute',
        left: 64,
        top: 414,
        width: 832,
        height: 66,
        padding: '20px 22px',
        backgroundColor: theme.primary,
        color: theme.text,
        opacity: 0.88,
        fontSize: 22,
        fontWeight: 700
      })
    ]
  )
}

function summaryFinal(spec) {
  const theme = colors(spec)
  const takeaways = list(spec, 'takeaways').slice(0, 3)
  return box(
    {
      width: CANVAS.width,
      height: CANVAS.height,
      position: 'relative',
      flexDirection: 'column',
      backgroundColor: theme.background,
      color: theme.text,
      fontFamily: DEFAULT_FONT_FAMILY,
      padding: '64px 72px'
    },
    [
      box({ position: 'absolute', left: 704, top: 54, width: 164, height: 164, borderRadius: 82, backgroundColor: theme.accent, opacity: 0.22 }),
      box({ position: 'absolute', left: 712, top: 286, flexDirection: 'row', alignItems: 'flex-end', gap: 12 }, [
        box({ width: 18, height: 30, backgroundColor: theme.primary, opacity: 0.72 }),
        box({ width: 18, height: 48, backgroundColor: theme.primary, opacity: 0.86 }),
        box({ width: 18, height: 66, backgroundColor: theme.accent, opacity: 0.92 })
      ]),
      Badge(text(spec, 'eyebrow', 'SUMMARY'), { color: theme.primary, fontSize: 18, fontWeight: 800, marginBottom: 24 }),
      Title(text(spec, 'title', 'Summary'), { width: 700, color: theme.text, fontSize: 50, fontWeight: 850, lineHeight: 1.08, marginBottom: 24 }),
      Subtitle(text(spec, 'subtitle', ''), { width: 640, color: theme.muted, fontSize: 23, marginBottom: 34 }),
      box(
        { flexDirection: 'row', gap: 18 },
        takeaways.map((item, index) =>
          StatCard({
            index: index + 1,
            label: item,
            color: theme.primary,
            textColor: theme.text,
            panelColor: theme.panel
          })
        )
      )
    ]
  )
}

function sectionTitle(spec) {
  const theme = colors(spec)
  return pageShell(spec, [
    box({ position: 'absolute', left: 72, top: 116, width: 8, height: 258, backgroundColor: theme.primary }),
    box({ position: 'absolute', left: 734, top: 74, width: 148, height: 148, backgroundColor: theme.accent, opacity: 0.2 }),
    box({ position: 'absolute', left: 734, top: 242, width: 148, height: 12, backgroundColor: theme.primary }),
    box({ marginLeft: 52, marginTop: 64 }, [pageHeader(spec, { titleWidth: 690, titleSize: 56 })])
  ])
}

function agendaList(spec) {
  const theme = colors(spec)
  const items = firstList(spec, ['items', 'takeaways'], ['Context', 'Evidence', 'Decision']).slice(0, 6)
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 760, titleSize: 42 }),
    box({ width: 724, flexDirection: 'column' }, numberedRows(items, theme, { max: 6 })),
    box({ position: 'absolute', right: 56, top: 126, width: 112, height: 310, backgroundColor: theme.primary, opacity: 0.12 })
  ])
}

function timelineSteps(spec) {
  const theme = colors(spec)
  const events = firstList(spec, ['events', 'steps', 'items'], ['Discover', 'Design', 'Deliver', 'Measure']).slice(0, 5)
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 760, titleSize: 40 }),
    box({ position: 'absolute', left: 110, top: 330, width: 740, height: 4, backgroundColor: theme.primary, opacity: 0.55 }),
    box(
      { position: 'absolute', left: 96, top: 254, flexDirection: 'row', gap: 22 },
      events.map((event, index) =>
        box({ width: 130, flexDirection: 'column', alignItems: 'center' }, [
          TextBlock(String(index + 1).padStart(2, '0'), {
            width: 52,
            height: 52,
            color: theme.text,
            backgroundColor: index % 2 ? theme.accent : theme.primary,
            fontSize: 20,
            fontWeight: 850,
            padding: '14px 0',
            textAlign: 'center',
            marginBottom: 18
          }),
          TextBlock(event, { color: theme.text, fontSize: 18, fontWeight: 700, textAlign: 'center', lineHeight: 1.18 })
        ])
      )
    )
  ])
}

function processFlow(spec) {
  const theme = colors(spec)
  const steps = firstList(spec, ['steps', 'items'], ['Input', 'Normalize', 'Render', 'Verify']).slice(0, 5)
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 730, titleSize: 40 }),
    box(
      { flexDirection: 'row', gap: 18, marginTop: 26 },
      steps.map((step, index) =>
        box({ width: 154, height: 172, flexDirection: 'column', backgroundColor: theme.panel, padding: 18 }, [
          TextBlock(String(index + 1), { color: theme.primary, fontSize: 28, fontWeight: 900, marginBottom: 20 }),
          TextBlock(step, { color: theme.text, fontSize: 21, fontWeight: 750, lineHeight: 1.15 }),
          box({ width: 48, height: 5, backgroundColor: index % 2 ? theme.accent : theme.primary, marginTop: 'auto' })
        ])
      )
    ),
    TextBlock(text(spec, 'conclusion', ''), {
      position: 'absolute',
      left: 74,
      bottom: 50,
      width: 812,
      minHeight: 48,
      color: theme.text,
      backgroundColor: theme.primary,
      opacity: 0.18,
      fontSize: 20,
      fontWeight: 750,
      padding: 14
    })
  ])
}

function metricDashboard(spec) {
  const theme = colors(spec)
  const metrics = firstList(spec, ['metrics', 'items'], ['Velocity +32%', 'Cost -18%', 'Quality 96%', 'Reach 4.2x']).slice(0, 6)
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 710, titleSize: 38 }),
    box(
      { flexDirection: 'row', flexWrap: 'wrap', gap: 18, marginTop: 6 },
      metrics.map((metric, index) => smallCard(`METRIC ${index + 1}`, metric, theme))
    )
  ])
}

function quoteFocus(spec) {
  const theme = colors(spec)
  return pageShell(spec, [
    TextBlock('“', { position: 'absolute', left: 60, top: 36, color: theme.primary, fontSize: 132, fontWeight: 900, opacity: 0.7 }),
    TextBlock(text(spec, 'quote', text(spec, 'title', 'A strong point belongs on a quiet page.')), {
      width: 720,
      marginTop: 116,
      marginLeft: 72,
      color: theme.text,
      fontSize: 42,
      fontWeight: 850,
      lineHeight: 1.13
    }),
    TextBlock(text(spec, 'attribution', ''), {
      marginLeft: 76,
      marginTop: 34,
      color: theme.muted,
      fontSize: 22,
      fontWeight: 700
    }),
    box({ position: 'absolute', right: 80, bottom: 72, width: 150, height: 10, backgroundColor: theme.accent })
  ])
}

function imageFeature(spec) {
  const theme = colors(spec)
  const points = firstList(spec, ['points', 'items'], ['Primary visual anchor', 'Caption explains evidence', 'Text stays out of the image']).slice(0, 3)
  return pageShell(spec, [
    box({ position: 'absolute', left: 56, top: 56, width: 452, height: 428, backgroundColor: theme.panel }),
    box({ position: 'absolute', left: 86, top: 86, width: 392, height: 268, backgroundColor: theme.primary, opacity: 0.18 }),
    TextBlock(text(spec, 'image_label', 'IMAGE'), { position: 'absolute', left: 226, top: 204, color: theme.primary, fontSize: 28, fontWeight: 900 }),
    TextBlock(text(spec, 'caption', ''), { position: 'absolute', left: 86, top: 386, width: 388, color: theme.muted, fontSize: 19, fontWeight: 650 }),
    box({ position: 'absolute', left: 548, top: 72, width: 330 }, [pageHeader(spec, { titleWidth: 330, titleSize: 38 })]),
    box({ position: 'absolute', left: 552, top: 280, width: 324, flexDirection: 'column' }, numberedRows(points, theme, { max: 3 }))
  ])
}

function researchPoster(spec) {
  const theme = colors(spec)
  const sections = firstList(spec, ['sections', 'items'], ['Context', 'Method', 'Result', 'Implication']).slice(0, 6)
  return pageShell(spec, [
    box({ position: 'absolute', left: 56, top: 42, width: 588 }, [pageHeader(spec, { titleWidth: 588, titleSize: 34, subtitleKey: 'authors' })]),
    box({ position: 'absolute', right: 70, top: 54, width: 140, height: 96, backgroundColor: theme.primary, opacity: 0.18 }),
    box(
      { position: 'absolute', left: 58, top: 194, flexDirection: 'row', gap: 20 },
      [0, 1, 2].map((column) =>
        box(
          { width: 268, flexDirection: 'column', gap: 14 },
          sections.slice(column * 2, column * 2 + 2).map((section, index) =>
            box({ height: 120, flexDirection: 'column', backgroundColor: theme.panel, padding: 16 }, [
              TextBlock(section, { color: theme.primary, fontSize: 20, fontWeight: 850, marginBottom: 12 }),
              TextBlock(column === 1 && index === 0 ? text(spec, 'key_visual', 'key visual') : 'Evidence block', {
                color: theme.muted,
                fontSize: 17,
                fontWeight: 600
              })
            ])
          )
        )
      )
    )
  ])
}

function dataStory(spec) {
  const theme = colors(spec)
  const metrics = firstList(spec, ['metrics', 'items'], ['North 42', 'South 35', 'West 28', 'East 19']).slice(0, 4)
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 600, titleSize: 38 }),
    box({ position: 'absolute', left: 86, top: 260, flexDirection: 'row', alignItems: 'flex-end', gap: 34 }, metrics.map((metric, index) =>
      box({ width: 112, flexDirection: 'column', alignItems: 'center' }, [
        box({ width: 64, height: 82 + index * 28, backgroundColor: index % 2 ? theme.accent : theme.primary, marginBottom: 18 }),
        TextBlock(metric, { color: theme.text, fontSize: 18, fontWeight: 750, textAlign: 'center' })
      ])
    )),
    TextBlock(text(spec, 'callout', ''), { position: 'absolute', right: 72, top: 184, width: 260, color: theme.text, backgroundColor: theme.panel, fontSize: 24, fontWeight: 850, lineHeight: 1.14, padding: 22 })
  ])
}

function riskAlert(spec) {
  const theme = colors(spec)
  const risks = firstList(spec, ['risks', 'items'], ['Scope drift', 'Dependency delay', 'Insufficient evidence']).slice(0, 4)
  return pageShell(spec, [
    TextBlock(text(spec, 'severity', 'L2'), { position: 'absolute', right: 70, top: 54, color: theme.text, backgroundColor: theme.primary, fontSize: 28, fontWeight: 900, padding: '14px 22px' }),
    pageHeader(spec, { titleWidth: 690, titleSize: 40 }),
    box({ width: 800, flexDirection: 'column', marginTop: 16 }, risks.map((risk, index) =>
      box({ height: 58, flexDirection: 'row', alignItems: 'center', backgroundColor: theme.panel, marginBottom: 14, padding: 16 }, [
        box({ width: 12, height: 34, backgroundColor: index === 0 ? theme.accent : theme.primary, marginRight: 16 }),
        TextBlock(risk, { color: theme.text, fontSize: 22, fontWeight: 760 })
      ])
    )),
    TextBlock(text(spec, 'summary', ''), { color: theme.muted, fontSize: 18, fontWeight: 650, marginTop: 6 })
  ])
}

function roadmapLanes(spec) {
  const theme = colors(spec)
  const lanes = firstList(spec, ['lanes', 'items'], ['Now', 'Next', 'Later']).slice(0, 4)
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 700, titleSize: 38 }),
    box({ flexDirection: 'column', gap: 16, marginTop: 16 }, lanes.map((lane, index) =>
      box({ width: 820, height: 62, flexDirection: 'row', alignItems: 'center', backgroundColor: theme.panel, padding: '0 18px' }, [
        TextBlock(lane, { width: 132, color: theme.primary, fontSize: 21, fontWeight: 850 }),
        box({ flex: 1, height: 12, backgroundColor: index % 2 ? theme.accent : theme.primary, opacity: 0.38 }),
        TextBlock(`Q${index + 1}`, { width: 54, color: theme.text, fontSize: 18, fontWeight: 800, textAlign: 'right' })
      ])
    ))
  ])
}

function architectureBlueprint(spec) {
  const theme = colors(spec)
  const nodes = firstList(spec, ['nodes', 'items'], ['Planner', 'CanvasSpec', 'Renderer', 'SVGlide']).slice(0, 6)
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 630, titleSize: 36 }),
    box(
      { position: 'absolute', left: 86, top: 240, flexDirection: 'row', flexWrap: 'wrap', gap: 24, width: 780 },
      nodes.map((item, index) =>
        box({ width: 236, height: 72, backgroundColor: theme.panel, borderWidth: 2, borderColor: index % 2 ? theme.accent : theme.primary, padding: 16 }, [
          TextBlock(item, { color: theme.text, fontSize: 20, fontWeight: 800 })
        ])
      )
    )
  ])
}

export function renderTree(spec) {
  if (spec.template_id === 'cover-hero') return coverHero(spec)
  if (spec.template_id === 'comparison-cards') return comparisonCards(spec)
  if (spec.template_id === 'summary-final') return summaryFinal(spec)
  if (spec.template_id === 'section-title') return sectionTitle(spec)
  if (spec.template_id === 'agenda-list') return agendaList(spec)
  if (spec.template_id === 'timeline-steps') return timelineSteps(spec)
  if (spec.template_id === 'process-flow') return processFlow(spec)
  if (spec.template_id === 'metric-dashboard') return metricDashboard(spec)
  if (spec.template_id === 'quote-focus') return quoteFocus(spec)
  if (spec.template_id === 'image-feature') return imageFeature(spec)
  if (spec.template_id === 'research-poster') return researchPoster(spec)
  if (spec.template_id === 'data-story') return dataStory(spec)
  if (spec.template_id === 'risk-alert') return riskAlert(spec)
  if (spec.template_id === 'roadmap-lanes') return roadmapLanes(spec)
  if (spec.template_id === 'architecture-blueprint') return architectureBlueprint(spec)
  throw new Error(`unsupported template_id for Satori adapter: ${spec.template_id}`)
}
