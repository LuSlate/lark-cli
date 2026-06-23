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
    muted: source.muted || '#CBD5E1',
    surface: source.surface || source.panel || '#111827'
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

function densePanelGrid(spec) {
  const theme = colors(spec)
  const metrics = firstList(spec, ['metrics', 'items'], ['Coverage 92', 'Latency -18%', 'Risk L2', 'Quality 4.6']).slice(0, 6)
  const notes = firstList(spec, ['notes', 'sections'], ['Signal held across cohorts', 'Bottleneck moved to onboarding', 'Next wave needs owner clarity']).slice(0, 3)
  return pageShell(spec, [
    box({ position: 'absolute', left: 56, top: 48, width: 848, height: 444, borderWidth: 3, borderColor: theme.text }),
    box({ position: 'absolute', left: 70, top: 62, width: 132, height: 88, backgroundColor: theme.panel, borderWidth: 2, borderColor: theme.primary }),
    TextBlock(text(spec, 'eyebrow', 'GRID REPORT').toUpperCase(), {
      position: 'absolute',
      left: 84,
      top: 88,
      width: 104,
      color: theme.text,
      fontSize: 17,
      fontWeight: 900,
      lineHeight: 1.1
    }),
    Title(text(spec, 'title', 'Dense Signal Grid'), {
      position: 'absolute',
      left: 226,
      top: 66,
      width: 620,
      color: theme.text,
      fontSize: 42,
      fontWeight: 900,
      lineHeight: 1.02
    }),
    TextBlock(text(spec, 'subtitle', ''), {
      position: 'absolute',
      left: 226,
      top: 158,
      width: 560,
      color: theme.muted,
      fontSize: 19,
      fontWeight: 700,
      lineHeight: 1.22
    }),
    box(
      { position: 'absolute', left: 70, top: 228, width: 548, flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
      metrics.map((metric, index) =>
        box({ width: 170, height: 82, flexDirection: 'column', backgroundColor: theme.panel, borderWidth: index % 3 === 0 ? 2 : 0, borderColor: theme.primary, padding: 14 }, [
          TextBlock(String(index + 1).padStart(2, '0'), { color: theme.primary, fontSize: 14, fontWeight: 850, marginBottom: 8 }),
          TextBlock(metric, { color: theme.text, fontSize: 19, fontWeight: 900, lineHeight: 1.08 })
        ])
      )
    ),
    box(
      { position: 'absolute', right: 70, top: 230, width: 252, flexDirection: 'column', gap: 12 },
      notes.map((note) =>
        box({ minHeight: 76, backgroundColor: theme.panel, borderWidth: 2, borderColor: theme.primary, padding: 14 }, [
          TextBlock(note, { color: theme.text, fontSize: 18, fontWeight: 900, lineHeight: 1.12 })
        ])
      )
    )
  ])
}

function executiveDashboard(spec) {
  const theme = colors(spec)
  const metrics = firstList(spec, ['metrics', 'items'], ['Revenue +14%', 'NDR 118%', 'Churn 2.1%', 'Pipeline 3.4x', 'QoQ +9%', 'NPS 48']).slice(0, 6)
  const bars = firstList(spec, ['bars', 'rankings'], ['Enterprise 82', 'Mid-market 64', 'SMB 48', 'Partner 36']).slice(0, 4)
  const barWidths = [236, 194, 154, 112]
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 710, titleSize: 40 }),
    box(
      { position: 'absolute', left: 68, top: 214, width: 548, flexDirection: 'row', flexWrap: 'wrap', gap: 14 },
      metrics.map((metric, index) =>
        box({ width: 170, height: 96, flexDirection: 'column', backgroundColor: theme.panel, borderWidth: 1, borderColor: theme.primary, padding: 16 }, [
          TextBlock(metric.split(' ').slice(-1)[0] || metric, { color: theme.primary, fontSize: 28, fontWeight: 900, lineHeight: 0.95, marginBottom: 12 }),
          TextBlock(metric, { color: theme.text, fontSize: 15, fontWeight: 750, lineHeight: 1.18 })
        ])
      )
    ),
    box({ position: 'absolute', right: 70, top: 214, width: 258, height: 290, flexDirection: 'column', backgroundColor: theme.panel, padding: 22 }, [
      TextBlock(text(spec, 'chart_title', 'Channel health'), { color: theme.text, fontSize: 22, fontWeight: 850, marginBottom: 20 }),
      ...bars.map((bar, index) =>
        box({ flexDirection: 'column', marginBottom: 16 }, [
          TextBlock(bar, { color: theme.muted, fontSize: 15, fontWeight: 700, marginBottom: 8 }),
          box({ width: 214, height: 12, backgroundColor: theme.background }, [
            box({ width: barWidths[index], height: 12, backgroundColor: theme.primary })
          ])
        ])
      )
    ])
  ])
}

function editorialQuoteChart(spec) {
  const theme = colors(spec)
  const points = firstList(spec, ['points', 'items'], ['Signal was visible before the metric moved', 'The constraint is organizational, not technical', 'Next action must be explicit']).slice(0, 3)
  return pageShell(spec, [
    box({ position: 'absolute', left: 54, top: 48, width: 852, height: 72, borderBottomWidth: 2, borderBottomColor: theme.primary }),
    TextBlock(text(spec, 'eyebrow', 'EDITORIAL').toUpperCase(), { position: 'absolute', left: 60, top: 72, color: theme.primary, fontSize: 16, fontWeight: 850 }),
    TextBlock(text(spec, 'section', 'FIELD NOTE'), { position: 'absolute', right: 62, top: 72, color: theme.muted, fontSize: 16, fontWeight: 750 }),
    TextBlock('“', { position: 'absolute', left: 58, top: 142, color: theme.primary, fontSize: 108, fontWeight: 900, lineHeight: 0.8 }),
    Title(text(spec, 'quote', text(spec, 'title', 'The operating model changed before the dashboard caught up.')), {
      position: 'absolute',
      left: 132,
      top: 148,
      width: 518,
      color: theme.text,
      fontSize: 43,
      fontWeight: 900,
      lineHeight: 1.04
    }),
    TextBlock(text(spec, 'attribution', ''), { position: 'absolute', left: 138, top: 352, width: 420, color: theme.muted, fontSize: 18, fontWeight: 750 }),
    box(
      { position: 'absolute', right: 70, top: 154, width: 212, flexDirection: 'column', gap: 14 },
      points.map((point, index) =>
        box({ minHeight: 78, flexDirection: 'row', backgroundColor: theme.panel, borderWidth: index === 0 ? 2 : 0, borderColor: theme.primary, padding: 14 }, [
          TextBlock(String(index + 1), { width: 32, color: theme.primary, fontSize: 26, fontWeight: 900 }),
          TextBlock(point, { flex: 1, color: theme.text, fontSize: 17, fontWeight: 760, lineHeight: 1.12 })
        ])
      )
    )
  ])
}

function ledgerBriefing(spec) {
  const theme = colors(spec)
  const items = firstList(spec, ['items', 'takeaways'], ['Scope closed', 'Evidence reviewed', 'Decision pending', 'Owner named']).slice(0, 5)
  const metrics = firstList(spec, ['metrics', 'stats'], ['Q2', '18%', '04']).slice(0, 3)
  return pageShell(spec, [
    box({ position: 'absolute', left: 56, top: 46, width: 848, height: 1, backgroundColor: theme.text }),
    box({ position: 'absolute', left: 56, bottom: 46, width: 848, height: 1, backgroundColor: theme.text }),
    TextBlock(text(spec, 'eyebrow', 'LEDGER').toUpperCase(), { position: 'absolute', left: 58, top: 70, color: theme.muted, fontSize: 15, fontWeight: 800 }),
    Title(text(spec, 'title', 'Operating Ledger'), {
      position: 'absolute',
      left: 56,
      top: 104,
      width: 520,
      color: theme.text,
      fontSize: 54,
      fontWeight: 300,
      lineHeight: 1.02
    }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 58, top: 230, width: 492, color: theme.muted, fontSize: 20, lineHeight: 1.35 }),
    box({ position: 'absolute', right: 62, top: 84, width: 250, flexDirection: 'row', gap: 18 }, metrics.map((metric) =>
      box({ width: 70, flexDirection: 'column', borderTopWidth: 1, borderTopColor: theme.text, paddingTop: 12 }, [
        TextBlock(metric, { color: theme.text, fontSize: 34, fontWeight: 300, lineHeight: 1 }),
        TextBlock('FIELD', { color: theme.muted, fontSize: 11, fontWeight: 800, marginTop: 8 })
      ])
    )),
    box({ position: 'absolute', right: 64, top: 222, width: 326, flexDirection: 'column' }, items.map((item, index) =>
      box({ height: 48, flexDirection: 'row', alignItems: 'center', borderTopWidth: 1, borderTopColor: theme.muted }, [
        TextBlock(String(index + 1).padStart(2, '0'), { width: 48, color: theme.muted, fontSize: 15, fontWeight: 800 }),
        TextBlock(item, { flex: 1, color: theme.text, fontSize: 18, fontWeight: 450, lineHeight: 1.18 })
      ])
    ))
  ])
}

function intelligenceBrief(spec) {
  const theme = colors(spec)
  const points = firstList(spec, ['points', 'signals', 'items'], ['Early signal', 'Structural constraint', 'Recommended action']).slice(0, 4)
  return pageShell(spec, [
    box({ position: 'absolute', left: 56, top: 56, width: 848, height: 52, borderBottomWidth: 1, borderBottomColor: theme.accent }),
    TextBlock(text(spec, 'eyebrow', 'PRIVATE BRIEF').toUpperCase(), { position: 'absolute', left: 62, top: 72, color: theme.accent, fontSize: 15, fontWeight: 850 }),
    TextBlock(text(spec, 'date', 'CONFIDENTIAL'), { position: 'absolute', right: 62, top: 72, color: theme.muted, fontSize: 15, fontWeight: 750 }),
    Title(text(spec, 'title', 'Signal Briefing'), { position: 'absolute', left: 70, top: 148, width: 602, color: theme.text, fontSize: 52, fontWeight: 700, lineHeight: 1.02 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 72, top: 282, width: 536, color: theme.muted, fontSize: 20, lineHeight: 1.32 }),
    box({ position: 'absolute', right: 72, top: 150, width: 238, flexDirection: 'column', gap: 14 }, points.map((point, index) =>
      box({ minHeight: 66, flexDirection: 'column', borderLeftWidth: 3, borderLeftColor: index === 0 ? theme.accent : theme.panel, paddingLeft: 14 }, [
        TextBlock(`S${index + 1}`, { color: theme.accent, fontSize: 14, fontWeight: 850, marginBottom: 8 }),
        TextBlock(point, { color: theme.text, fontSize: 18, fontWeight: 650, lineHeight: 1.14 })
      ])
    )),
    box({ position: 'absolute', left: 72, bottom: 70, width: 720, height: 1, backgroundColor: theme.accent, opacity: 0.7 })
  ])
}

function printedProgram(spec) {
  const theme = colors(spec)
  const items = firstList(spec, ['items', 'courses', 'agenda'], ['Opening note', 'Main course', 'Decision round', 'Closing']).slice(0, 5)
  return pageShell(spec, [
    box({ position: 'absolute', left: 58, top: 50, width: 844, height: 438, borderWidth: 2, borderColor: theme.primary }),
    TextBlock(text(spec, 'edition', 'EDITION 01'), { position: 'absolute', left: 84, top: 80, color: theme.primary, fontSize: 17, fontWeight: 900 }),
    Title(text(spec, 'title', 'Long Table Review').toUpperCase(), { position: 'absolute', left: 82, top: 120, width: 514, color: theme.primary, fontSize: 54, fontWeight: 900, lineHeight: 0.92 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 86, top: 288, width: 430, color: theme.text, fontSize: 20, lineHeight: 1.35 }),
    box({ position: 'absolute', right: 82, top: 88, width: 292, flexDirection: 'column' }, items.map((item, index) =>
      box({ minHeight: 66, borderBottomWidth: 1, borderBottomColor: theme.primary, padding: '10px 0', flexDirection: 'row' }, [
        TextBlock(String(index + 1).padStart(2, '0'), { width: 42, color: theme.primary, fontSize: 24, fontWeight: 800 }),
        TextBlock(item.toUpperCase(), { flex: 1, color: theme.primary, fontSize: 20, fontWeight: 850, lineHeight: 1.05 })
      ])
    )),
    TextBlock(text(spec, 'footer', 'SVGlide program note'), { position: 'absolute', left: 86, bottom: 76, color: theme.muted, fontSize: 16, fontWeight: 700 })
  ])
}

function retroUiDashboard(spec) {
  const theme = colors(spec)
  const panels = firstList(spec, ['panels', 'items'], ['Build status: OK', 'Open issues: 12', 'Owner: Platform']).slice(0, 4)
  return box({ width: CANVAS.width, height: CANVAS.height, position: 'relative', flexDirection: 'column', backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 48 }, [
    box({ position: 'absolute', left: 70, top: 62, width: 820, height: 416, backgroundColor: theme.panel, borderWidth: 3, borderColor: theme.text }),
    box({ position: 'absolute', left: 76, top: 68, width: 808, height: 38, backgroundColor: theme.primary, flexDirection: 'row', alignItems: 'center', padding: '0 12px' }, [
      TextBlock(text(spec, 'window_title', 'SVGLIDE.EXE'), { color: theme.accent, fontSize: 18, fontWeight: 850 })
    ]),
    Title(text(spec, 'title', 'Release Control Panel'), { position: 'absolute', left: 96, top: 132, width: 500, color: theme.text, fontSize: 38, fontWeight: 800, lineHeight: 1.08 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 98, top: 228, width: 428, color: theme.muted, fontSize: 19, lineHeight: 1.28 }),
    box({ position: 'absolute', right: 98, top: 132, width: 292, flexDirection: 'column', gap: 12 }, panels.map((panel) =>
      box({ height: 62, backgroundColor: theme.background, borderWidth: 2, borderColor: theme.text, padding: 14 }, [
        TextBlock(panel, { color: theme.text, fontSize: 18, fontWeight: 750 })
      ])
    )),
    box({ position: 'absolute', left: 96, bottom: 88, width: 768, height: 28, backgroundColor: theme.background, borderWidth: 2, borderColor: theme.text }, [
      TextBlock(text(spec, 'status', 'READY'), { color: theme.primary, fontSize: 15, fontWeight: 900, padding: '5px 10px' })
    ])
  ])
}

function productRibbon(spec) {
  const theme = colors(spec)
  const cards = firstList(spec, ['cards', 'items'], ['Feature A', 'Feature B', 'Feature C']).slice(0, 4)
  const stripeColors = [theme.primary, theme.accent, theme.panel, theme.muted]
  const labelColors = [theme.primary, theme.accent, theme.text, theme.primary]
  return pageShell(spec, [
    box({ position: 'absolute', left: 0, top: 0, width: CANVAS.width, height: 28, flexDirection: 'row' }, stripeColors.map((color) =>
      box({ width: 240, height: 28, backgroundColor: color })
    )),
    TextBlock(text(spec, 'eyebrow', 'CATALOG').toUpperCase(), { position: 'absolute', left: 64, top: 70, color: theme.primary, fontSize: 16, fontWeight: 900 }),
    Title(text(spec, 'title', 'Product Catalog'), { position: 'absolute', left: 62, top: 102, width: 610, color: theme.text, fontSize: 58, fontWeight: 900, lineHeight: 0.92 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 66, top: 238, width: 470, color: theme.muted, fontSize: 20, lineHeight: 1.28 }),
    box({ position: 'absolute', left: 64, bottom: 62, flexDirection: 'row', gap: 16 }, cards.map((card, index) =>
      box({ width: 194, height: 118, backgroundColor: index % 2 ? theme.panel : theme.background, borderWidth: 2, borderColor: theme.text, padding: 14 }, [
        TextBlock(String(index + 1).padStart(2, '0'), { color: labelColors[index % labelColors.length], fontSize: 24, fontWeight: 900, marginBottom: 12 }),
        TextBlock(card, { color: theme.text, fontSize: 18, fontWeight: 850, lineHeight: 1.08 })
      ])
    )),
    box({ position: 'absolute', right: 78, top: 94, width: 112, height: 112, borderRadius: 56, backgroundColor: theme.panel, borderWidth: 2, borderColor: theme.accent, alignItems: 'center', justifyContent: 'center' }, [
      TextBlock(text(spec, 'seal', 'NEW'), { color: theme.text, fontSize: 25, fontWeight: 900 })
    ])
  ])
}

function typeMassPoster(spec) {
  const theme = colors(spec)
  const notes = firstList(spec, ['notes', 'items'], ['One message', 'No decoration', 'High contrast']).slice(0, 3)
  return box({ width: CANVAS.width, height: CANVAS.height, position: 'relative', flexDirection: 'column', backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 52 }, [
    box({ position: 'absolute', left: 52, top: 48, width: 856, height: 1, backgroundColor: theme.primary, opacity: 0.62 }),
    TextBlock(text(spec, 'eyebrow', 'STUDIO').toUpperCase(), { position: 'absolute', left: 58, top: 66, color: theme.primary, fontSize: 15, fontWeight: 850 }),
    TextBlock(text(spec, 'counter', '01/06'), { position: 'absolute', right: 58, top: 66, color: theme.primary, fontSize: 15, fontWeight: 850 }),
    Title(text(spec, 'title', 'MAKE IT LOUD').toUpperCase(), { position: 'absolute', left: 58, top: 118, width: 800, color: theme.primary, fontSize: 82, fontWeight: 900, lineHeight: 0.88 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 62, bottom: 120, width: 520, color: theme.muted, fontSize: 21, lineHeight: 1.25 }),
    box({ position: 'absolute', right: 70, bottom: 78, width: 248, flexDirection: 'column' }, notes.map((note) =>
      box({ borderTopWidth: 2, borderTopColor: theme.primary, padding: '12px 0' }, [
        TextBlock(note.toUpperCase(), { color: theme.primary, fontSize: 18, fontWeight: 900, lineHeight: 1.05 })
      ])
    ))
  ])
}

function brutalistMatrix(spec) {
  const theme = colors(spec)
  const cells = firstList(spec, ['cells', 'items'], ['Price clarity', 'Time to value', 'Risk level', 'Owner fit', 'Migration cost', 'Evidence depth']).slice(0, 6)
  return box({ width: CANVAS.width, height: CANVAS.height, position: 'relative', flexDirection: 'column', backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 50 }, [
    box({ position: 'absolute', left: 50, top: 50, width: 860, height: 440, borderWidth: 3, borderColor: theme.text }),
    TextBlock(text(spec, 'eyebrow', 'MATRIX').toUpperCase(), { position: 'absolute', left: 70, top: 74, color: theme.text, fontSize: 15, fontWeight: 900 }),
    Title(text(spec, 'title', 'Decision Matrix').toUpperCase(), { position: 'absolute', left: 70, top: 104, width: 492, color: theme.text, fontSize: 50, fontWeight: 900, lineHeight: 0.96 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 70, top: 222, width: 426, color: theme.muted, fontSize: 19, lineHeight: 1.22 }),
    box({ position: 'absolute', right: 72, top: 76, width: 314, height: 92, backgroundColor: theme.panel, borderWidth: 3, borderColor: theme.primary, padding: 14 }, [
      TextBlock(text(spec, 'callout', 'BEST OPTION').toUpperCase(), { color: theme.text, fontSize: 24, fontWeight: 900, lineHeight: 1 })
    ]),
    box({ position: 'absolute', left: 70, bottom: 76, width: 820, flexDirection: 'row', flexWrap: 'wrap' }, cells.map((cell, index) =>
      box({ width: 273, height: 74, borderWidth: 2, borderColor: theme.text, backgroundColor: index % 2 ? theme.panel : theme.background, padding: 12, flexDirection: 'row' }, [
        TextBlock(String(index + 1), { width: 34, color: theme.primary, fontSize: 28, fontWeight: 900 }),
        TextBlock(cell, { flex: 1, color: theme.text, fontSize: 18, fontWeight: 850, lineHeight: 1.08 })
      ])
    ))
  ])
}

function annotatedFieldBoard(spec) {
  const theme = colors(spec)
  const notes = firstList(spec, ['notes', 'items'], ['Interview signal', 'Evidence needs follow-up', 'Decision owner named']).slice(0, 4)
  return pageShell(spec, [
    box({ position: 'absolute', left: 62, top: 56, width: 836, height: 428, borderWidth: 2, borderColor: theme.muted, backgroundColor: theme.panel }),
    TextBlock(text(spec, 'eyebrow', 'FIELD BOARD').toUpperCase(), { position: 'absolute', left: 86, top: 84, color: theme.primary, fontSize: 16, fontWeight: 900 }),
    Title(text(spec, 'title', 'Annotated Evidence'), { position: 'absolute', left: 86, top: 116, width: 520, color: theme.text, fontSize: 48, fontWeight: 850, lineHeight: 1.02 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 88, top: 228, width: 430, color: theme.muted, fontSize: 20, lineHeight: 1.28 }),
    TextBlock(text(spec, 'stamp', 'REVIEWED').toUpperCase(), { position: 'absolute', right: 90, top: 86, color: theme.primary, borderWidth: 3, borderColor: theme.primary, fontSize: 22, fontWeight: 900, padding: '10px 14px' }),
    box({ position: 'absolute', right: 86, top: 160, width: 302, flexDirection: 'column', gap: 14 }, notes.map((note, index) =>
      box({ minHeight: 66, backgroundColor: theme.background, borderWidth: 2, borderColor: theme.text, padding: 14 }, [
        TextBlock(`NOTE ${index + 1}`, { color: theme.primary, fontSize: 13, fontWeight: 900, marginBottom: 8 }),
        TextBlock(note, { color: theme.text, fontSize: 18, fontWeight: 750, lineHeight: 1.12 })
      ])
    )),
    box({ position: 'absolute', left: 86, bottom: 82, width: 430, flexDirection: 'row', gap: 12 }, firstList(spec, ['tags'], ['USER', 'EVIDENCE', 'NEXT']).slice(0, 3).map((tag) =>
      TextBlock(tag.toUpperCase(), { color: theme.text, backgroundColor: theme.panel, fontSize: 14, fontWeight: 900, padding: '8px 12px' })
    ))
  ])
}

function architecturalSpec(spec) {
  const theme = colors(spec)
  const rows = firstList(spec, ['rows', 'items'], ['Foundation', 'Structure', 'Interface', 'Handoff']).slice(0, 4)
  return pageShell(spec, [
    box({ position: 'absolute', left: 70, top: 62, width: 820, height: 414, borderWidth: 1, borderColor: theme.muted }),
    box({ position: 'absolute', left: 92, top: 86, width: 258, height: 258, borderWidth: 2, borderColor: theme.primary }),
    box({ position: 'absolute', left: 142, top: 136, width: 158, height: 158, borderRadius: 79, borderWidth: 2, borderColor: theme.accent }),
    TextBlock(text(spec, 'eyebrow', 'SPEC').toUpperCase(), { position: 'absolute', left: 392, top: 90, color: theme.muted, fontSize: 15, fontWeight: 850 }),
    Title(text(spec, 'title', 'Architecture Spec'), { position: 'absolute', left: 390, top: 124, width: 430, color: theme.text, fontSize: 46, fontWeight: 650, lineHeight: 1.03 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 392, top: 238, width: 396, color: theme.muted, fontSize: 20, lineHeight: 1.32 }),
    box({ position: 'absolute', left: 92, bottom: 84, width: 746, flexDirection: 'row', gap: 14 }, rows.map((row, index) =>
      box({ width: 176, height: 70, borderTopWidth: 1, borderTopColor: theme.primary, paddingTop: 12 }, [
        TextBlock(String(index + 1).padStart(2, '0'), { color: theme.primary, fontSize: 16, fontWeight: 850, marginBottom: 8 }),
        TextBlock(row, { color: theme.text, fontSize: 18, fontWeight: 700, lineHeight: 1.1 })
      ])
    ))
  ])
}

function trendGridReport(spec) {
  const theme = colors(spec)
  const trends = firstList(spec, ['trends', 'items'], ['Model cost pressure', 'Agent workflows', 'Design ops maturity', 'Governance gaps']).slice(0, 4)
  return pageShell(spec, [
    box({ position: 'absolute', left: 52, top: 52, width: 856, height: 436, borderWidth: 2, borderColor: theme.primary, opacity: 0.9 }),
    TextBlock(text(spec, 'eyebrow', 'TREND INDEX').toUpperCase(), { position: 'absolute', left: 72, top: 74, color: theme.primary, fontSize: 15, fontWeight: 900 }),
    Title(text(spec, 'title', 'Cobalt Trend Report'), { position: 'absolute', left: 70, top: 112, width: 570, color: theme.primary, fontSize: 58, fontWeight: 500, lineHeight: 0.94 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 72, top: 250, width: 500, color: theme.muted, fontSize: 19, lineHeight: 1.3 }),
    box({ position: 'absolute', right: 74, top: 92, width: 170, height: 170, flexDirection: 'row', flexWrap: 'wrap' }, Array.from({ length: 16 }).map((_, index) =>
      box({ width: 34, height: 34, backgroundColor: index % 3 === 0 ? theme.primary : theme.panel, marginRight: 4, marginBottom: 4, opacity: index % 3 === 0 ? 1 : 0.42 })
    )),
    box({ position: 'absolute', left: 72, bottom: 74, width: 810, flexDirection: 'column' }, trends.map((trend, index) =>
      box({ height: 42, flexDirection: 'row', alignItems: 'center', borderTopWidth: 1, borderTopColor: theme.primary }, [
        TextBlock(`0${index + 1}`, { width: 54, color: theme.primary, fontSize: 16, fontWeight: 850 }),
        TextBlock(trend, { flex: 1, color: theme.text, fontSize: 19, fontWeight: 650 }),
        TextBlock(index % 2 ? 'RISING' : 'WATCH', { width: 94, color: theme.primary, fontSize: 13, fontWeight: 900, textAlign: 'right' })
      ])
    ))
  ])
}

function serifStatEditorial(spec) {
  const theme = colors(spec)
  const cards = firstList(spec, ['cards', 'items'], ['Quality held', 'Narrative simplified', 'Next evidence needed']).slice(0, 3)
  return pageShell(spec, [
    TextBlock(text(spec, 'eyebrow', 'EDITORIAL').toUpperCase(), { position: 'absolute', left: 70, top: 72, color: theme.primary, fontSize: 16, fontWeight: 900 }),
    Title(text(spec, 'stat', '73%'), { position: 'absolute', left: 68, top: 104, width: 360, color: theme.primary, fontSize: 118, fontWeight: 500, lineHeight: 0.9 }),
    Title(text(spec, 'title', 'Evidence moved the decision'), { position: 'absolute', left: 442, top: 104, width: 380, color: theme.text, fontSize: 44, fontWeight: 600, lineHeight: 1.02 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 444, top: 238, width: 360, color: theme.muted, fontSize: 20, lineHeight: 1.32 }),
    box({ position: 'absolute', left: 70, bottom: 70, flexDirection: 'row', gap: 18 }, cards.map((card, index) =>
      box({ width: 252, minHeight: 112, borderTopWidth: 3, borderTopColor: index === 0 ? theme.accent : theme.primary, backgroundColor: theme.panel, padding: 16 }, [
        TextBlock(card, { color: theme.text, fontSize: 22, fontWeight: 650, lineHeight: 1.12 })
      ])
    ))
  ])
}

function posterStatPunch(spec) {
  const theme = colors(spec)
  const pillars = firstList(spec, ['pillars', 'items'], ['Bold claim', 'Evidence block', 'Next move']).slice(0, 3)
  return box({ width: CANVAS.width, height: CANVAS.height, position: 'relative', flexDirection: 'column', backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 52 }, [
    box({ position: 'absolute', left: 48, top: 48, width: 864, height: 444, borderWidth: 3, borderColor: theme.text }),
    TextBlock(text(spec, 'eyebrow', 'POSTER').toUpperCase(), { position: 'absolute', left: 72, top: 72, color: theme.text, fontSize: 16, fontWeight: 900 }),
    Title(text(spec, 'title', 'Make the call').toUpperCase(), { position: 'absolute', left: 70, top: 104, width: 610, color: theme.text, fontSize: 66, fontWeight: 900, lineHeight: 0.9 }),
    Title(text(spec, 'stat', '3X'), { position: 'absolute', right: 82, top: 96, width: 184, color: theme.primary, fontSize: 118, fontWeight: 900, lineHeight: 0.86 }),
    TextBlock(text(spec, 'subtitle', ''), { position: 'absolute', left: 74, top: 272, width: 470, color: theme.muted, fontSize: 20, lineHeight: 1.28 }),
    box({ position: 'absolute', left: 74, bottom: 76, flexDirection: 'row', gap: 16 }, pillars.map((pillar, index) =>
      box({ width: 250, minHeight: 86, borderTopWidth: 3, borderTopColor: theme.primary, paddingTop: 12 }, [
        TextBlock(`0${index + 1}`, { color: theme.primary, fontSize: 28, fontWeight: 900, marginBottom: 6 }),
        TextBlock(pillar, { color: theme.text, fontSize: 20, fontWeight: 850, lineHeight: 1.08 })
      ])
    ))
  ])
}

const BEAUTIFUL_TEMPLATE_CONFIGS = {
  'pixel-orbit-console': { mode: 'console', label: 'ORBIT CONSOLE', listKeys: ['stats', 'actions', 'badges'] },
  'biennale-programme-poster': { mode: 'programme', label: 'PROGRAMME', listKeys: ['programme'] },
  'block-frame-grid': { mode: 'block-grid', label: 'BLOCK FRAME', listKeys: ['cards', 'stats'] },
  'capsule-card-system': { mode: 'capsule', label: 'CAPSULES', listKeys: ['capsules', 'steps'] },
  'coral-magazine-feature': { mode: 'magazine', label: 'FEATURE', listKeys: ['cards'] },
  'creative-mode-grid': { mode: 'creative-grid', label: 'CREATIVE MODE', listKeys: ['sections', 'metrics'] },
  'daisy-workshop-playbook': { mode: 'soft-workshop', label: 'PLAYBOOK', listKeys: ['lessons', 'notes'] },
  'tritone-editorial-spread': { mode: 'tritone', label: 'TRITONE', listKeys: ['points'] },
  'emerald-editorial-cover': { mode: 'cover-editorial', label: 'LEADERSHIP', listKeys: ['stats', 'points'] },
  'grove-organic-brief': { mode: 'organic', label: 'GROVE', listKeys: ['principles', 'metrics'] },
  'mat-midcentury-board': { mode: 'midcentury', label: 'MAT BOARD', listKeys: ['cards', 'timeline'] },
  'people-platform-manifesto': { mode: 'manifesto', label: 'PLATFORM', listKeys: ['platforms', 'actions'] },
  'pink-nocturne-feature': { mode: 'nocturne', label: 'NOCTURNE', listKeys: ['sections'] },
  'playful-indie-launch': { mode: 'playful', label: 'INDIE LAUNCH', listKeys: ['stats', 'steps'] },
  'retro-zine-spread': { mode: 'zine', label: 'ZINE', listKeys: ['notes'] },
  'sticky-workshop-board': { mode: 'sticky', label: 'WORKSHOP', listKeys: ['postits', 'phases'] },
  'soft-editorial-feature': { mode: 'soft-editorial', label: 'ESSAY', listKeys: ['cards'] },
  'stencil-field-manual': { mode: 'manual', label: 'FIELD MANUAL', listKeys: ['principles', 'rows'] },
  'vellum-scholar-brief': { mode: 'scholar', label: 'SCHOLAR BRIEF', listKeys: ['notes', 'stats'] }
}

function firstConfiguredItems(spec, cfg, fallback = ['Signal', 'Evidence', 'Next move']) {
  return firstList(spec, cfg.listKeys || ['items'], fallback)
}

function templateBadge(spec, cfg, style = {}) {
  const theme = colors(spec)
  return TextBlock(text(spec, 'eyebrow', cfg.label).toUpperCase(), {
    color: theme.primary,
    fontSize: 15,
    fontWeight: 900,
    letterSpacing: 0,
    ...style
  })
}

function beautifulTemplate(spec, cfg) {
  const theme = colors(spec)
  const items = firstConfiguredItems(spec, cfg).slice(0, 6)
  const title = text(spec, 'title', 'Untitled')
  const subtitle = text(spec, 'subtitle', '')
  const quote = text(spec, 'quote', text(spec, 'lede', ''))
  const stat = text(spec, 'stat', items[0] || '')

  if (cfg.mode === 'console') {
    return box({ width: CANVAS.width, height: CANVAS.height, position: 'relative', backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 48 }, [
      box({ position: 'absolute', left: 38, top: 34, width: 884, height: 472, borderWidth: 3, borderColor: theme.primary, backgroundColor: theme.panel }),
      box({ position: 'absolute', left: 70, top: 70, width: 820, height: 34, flexDirection: 'row', gap: 10 }, Array.from({ length: 18 }).map((_, index) =>
        box({ width: index % 4 === 0 ? 56 : 28, height: 10, backgroundColor: index % 3 === 0 ? theme.accent : theme.primary, opacity: index % 2 ? 0.42 : 0.78 })
      )),
      templateBadge(spec, cfg, { position: 'absolute', left: 76, top: 122 }),
      Title(title, { position: 'absolute', left: 74, top: 154, width: 548, color: theme.text, fontSize: 52, fontWeight: 900, lineHeight: 0.96 }),
      TextBlock(subtitle, { position: 'absolute', left: 76, top: 278, width: 480, color: theme.muted, fontSize: 20, lineHeight: 1.24 }),
      box({ position: 'absolute', right: 76, top: 130, width: 236, flexDirection: 'column', gap: 12 }, items.slice(0, 4).map((item, index) =>
        box({ minHeight: 54, borderWidth: 2, borderColor: index % 2 ? theme.accent : theme.primary, backgroundColor: theme.background, padding: 12 }, [
          TextBlock(item, { color: theme.text, fontSize: 18, fontWeight: 800, lineHeight: 1.1 })
        ])
      )),
      TextBlock('PX', { position: 'absolute', left: 76, bottom: 64, color: theme.accent, fontSize: 56, fontWeight: 900 })
    ])
  }

  if (cfg.mode === 'programme' || cfg.mode === 'manual') {
    return pageShell(spec, [
      box({ position: 'absolute', left: 58, top: 52, width: 844, height: 438, borderWidth: cfg.mode === 'manual' ? 3 : 2, borderColor: theme.primary }),
      templateBadge(spec, cfg, { position: 'absolute', left: 82, top: 78 }),
      Title(title, { position: 'absolute', left: 80, top: 112, width: cfg.mode === 'manual' ? 382 : 500, color: theme.text, fontSize: cfg.mode === 'manual' ? 46 : 58, fontWeight: 850, lineHeight: 0.96 }),
      TextBlock(subtitle, { position: 'absolute', left: 82, top: cfg.mode === 'manual' ? 232 : 254, width: 390, color: theme.muted, fontSize: 19, lineHeight: 1.28 }),
      box({ position: 'absolute', right: 80, top: 84, width: 330, flexDirection: 'column' }, items.slice(0, 5).map((item, index) =>
        box({ minHeight: 58, flexDirection: 'row', alignItems: 'center', borderTopWidth: 2, borderTopColor: theme.primary, padding: '10px 0' }, [
          TextBlock(String(index + 1).padStart(2, '0'), { width: 48, color: theme.accent, fontSize: 18, fontWeight: 900 }),
          TextBlock(item, { flex: 1, color: theme.text, fontSize: 19, fontWeight: 750, lineHeight: 1.12 })
        ])
      )),
      TextBlock(text(spec, 'footer', text(spec, 'venue', '')), { position: 'absolute', left: 82, bottom: 78, width: 430, color: theme.primary, fontSize: 17, fontWeight: 850 })
    ])
  }

  if (cfg.mode === 'block-grid' || cfg.mode === 'creative-grid' || cfg.mode === 'capsule' || cfg.mode === 'sticky') {
    const rounded = cfg.mode === 'capsule' ? 999 : cfg.mode === 'sticky' ? 2 : 0
    const roundedStyle = rounded ? { borderRadius: rounded } : {}
    return pageShell(spec, [
      templateBadge(spec, cfg, { position: 'absolute', left: 70, top: 66 }),
      Title(title, { position: 'absolute', left: 68, top: 96, width: 520, color: theme.text, fontSize: 48, fontWeight: 900, lineHeight: 0.98 }),
      TextBlock(subtitle, { position: 'absolute', left: 70, top: 210, width: 480, color: theme.muted, fontSize: 19, lineHeight: 1.28 }),
      box({ position: 'absolute', right: 70, top: 70, width: 248, height: 138, backgroundColor: theme.accent, opacity: cfg.mode === 'sticky' ? 0.36 : 0.92, ...roundedStyle }),
      box({ position: 'absolute', left: 70, bottom: 66, width: 820, flexDirection: 'row', flexWrap: 'wrap', gap: 14 }, items.slice(0, 6).map((item, index) =>
        box({ width: cfg.mode === 'sticky' ? 246 : 258, minHeight: cfg.mode === 'capsule' ? 58 : 76, backgroundColor: index % 2 ? theme.surface : theme.panel, borderWidth: 2, borderColor: theme.primary, padding: 14, ...roundedStyle }, [
          TextBlock(item, { color: theme.text, fontSize: 18, fontWeight: 800, lineHeight: 1.1 })
        ])
      ))
    ])
  }

  if (cfg.mode === 'cover-editorial' || cfg.mode === 'manifesto' || cfg.mode === 'nocturne') {
    return box({ width: CANVAS.width, height: CANVAS.height, position: 'relative', backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 54 }, [
      templateBadge(spec, cfg, { position: 'absolute', left: 76, top: 70, color: cfg.mode === 'manifesto' ? theme.text : theme.primary }),
      Title(title.toUpperCase(), { position: 'absolute', left: 74, top: 108, width: cfg.mode === 'manifesto' ? 720 : 620, color: theme.text, fontSize: cfg.mode === 'manifesto' ? 64 : 58, fontWeight: 900, lineHeight: 0.9 }),
      TextBlock(subtitle, { position: 'absolute', left: 78, top: 276, width: 510, color: theme.muted, fontSize: 20, lineHeight: 1.25 }),
      box({ position: 'absolute', right: 78, top: 86, width: 210, height: 210, borderWidth: 3, borderColor: theme.primary, backgroundColor: cfg.mode === 'manifesto' ? theme.accent : theme.panel }),
      TextBlock(stat || cfg.label, { position: 'absolute', right: 94, top: 142, width: 178, color: cfg.mode === 'manifesto' ? theme.background : theme.primary, fontSize: 34, fontWeight: 900, lineHeight: 1.0, textAlign: 'center' }),
      box({ position: 'absolute', left: 78, bottom: 70, flexDirection: 'row', gap: 14 }, items.slice(0, 3).map((item, index) =>
        box({ width: 250, minHeight: 82, borderTopWidth: 3, borderTopColor: index === 0 ? theme.accent : theme.primary, paddingTop: 12 }, [
          TextBlock(item, { color: theme.text, fontSize: 20, fontWeight: 820, lineHeight: 1.08 })
        ])
      ))
    ])
  }

  if (cfg.mode === 'organic' || cfg.mode === 'midcentury' || cfg.mode === 'playful') {
    return pageShell(spec, [
      box({ position: 'absolute', left: 62, top: 58, width: 318, height: 424, backgroundColor: theme.panel }),
      box({ position: 'absolute', left: 96, top: 92, width: 248, height: 154, backgroundColor: theme.surface, borderWidth: 2, borderColor: theme.primary }),
      templateBadge(spec, cfg, { position: 'absolute', left: 418, top: 76 }),
      Title(title, { position: 'absolute', left: 416, top: 112, width: 430, color: theme.text, fontSize: 46, fontWeight: 760, lineHeight: 1.0 }),
      TextBlock(subtitle, { position: 'absolute', left: 418, top: 234, width: 386, color: theme.muted, fontSize: 19, lineHeight: 1.3 }),
      box({ position: 'absolute', left: 416, bottom: 70, width: 410, flexDirection: 'column', gap: 12 }, items.slice(0, 3).map((item, index) =>
        box({ minHeight: 52, flexDirection: 'row', alignItems: 'center' }, [
          box({ width: 18, height: 18, borderRadius: cfg.mode === 'midcentury' ? 0 : 9, backgroundColor: index % 2 ? theme.accent : theme.primary, marginRight: 14 }),
          TextBlock(item, { flex: 1, color: theme.text, fontSize: 20, fontWeight: 750, lineHeight: 1.12 })
        ])
      ))
    ])
  }

  if (cfg.mode === 'zine' || cfg.mode === 'soft-workshop') {
    return pageShell(spec, [
      box({ position: 'absolute', left: 70, top: 62, width: 364, height: 416, backgroundColor: theme.panel, borderWidth: 2, borderColor: theme.primary }),
      box({ position: 'absolute', left: 104, top: 94, width: 296, height: 120, backgroundColor: theme.surface }),
      templateBadge(spec, cfg, { position: 'absolute', left: 470, top: 76 }),
      Title(title, { position: 'absolute', left: 468, top: 112, width: 360, color: theme.text, fontSize: 44, fontWeight: 820, lineHeight: 1.0 }),
      TextBlock(quote || subtitle, { position: 'absolute', left: 470, top: 244, width: 342, color: theme.muted, fontSize: 21, fontWeight: 650, lineHeight: 1.22 }),
      box({ position: 'absolute', left: 470, bottom: 72, flexDirection: 'row', gap: 12 }, items.slice(0, 3).map((item) =>
        box({ width: 112, minHeight: 92, backgroundColor: theme.surface, borderWidth: 2, borderColor: theme.primary, padding: 10 }, [
          TextBlock(item, { color: theme.text, fontSize: 16, fontWeight: 800, lineHeight: 1.1 })
        ])
      ))
    ])
  }

  return pageShell(spec, [
    templateBadge(spec, cfg, { position: 'absolute', left: 72, top: 70 }),
    Title(title, { position: 'absolute', left: 70, top: 108, width: 600, color: theme.text, fontSize: cfg.mode === 'scholar' ? 50 : 46, fontWeight: 780, lineHeight: 1.02 }),
    TextBlock(quote || subtitle, { position: 'absolute', left: 72, top: 242, width: 560, color: theme.muted, fontSize: 21, lineHeight: 1.3 }),
    box({ position: 'absolute', right: 76, top: 78, width: 170, height: 330, borderWidth: 2, borderColor: theme.primary, backgroundColor: theme.panel }),
    box({ position: 'absolute', left: 72, bottom: 72, flexDirection: 'row', gap: 16 }, items.slice(0, 3).map((item, index) =>
      box({ width: 244, minHeight: 86, borderTopWidth: 3, borderTopColor: index === 0 ? theme.accent : theme.primary, paddingTop: 12 }, [
        TextBlock(item, { color: theme.text, fontSize: 20, fontWeight: 740, lineHeight: 1.1 })
      ])
    ))
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
  if (spec.template_id === 'dense-panel-grid') return densePanelGrid(spec)
  if (spec.template_id === 'executive-dashboard') return executiveDashboard(spec)
  if (spec.template_id === 'editorial-quote-chart') return editorialQuoteChart(spec)
  if (spec.template_id === 'ledger-briefing') return ledgerBriefing(spec)
  if (spec.template_id === 'intelligence-brief') return intelligenceBrief(spec)
  if (spec.template_id === 'printed-program') return printedProgram(spec)
  if (spec.template_id === 'retro-ui-dashboard') return retroUiDashboard(spec)
  if (spec.template_id === 'product-ribbon') return productRibbon(spec)
  if (spec.template_id === 'type-mass-poster') return typeMassPoster(spec)
  if (spec.template_id === 'brutalist-matrix') return brutalistMatrix(spec)
  if (spec.template_id === 'annotated-field-board') return annotatedFieldBoard(spec)
  if (spec.template_id === 'architectural-spec') return architecturalSpec(spec)
  if (spec.template_id === 'trend-grid-report') return trendGridReport(spec)
  if (spec.template_id === 'serif-stat-editorial') return serifStatEditorial(spec)
  if (spec.template_id === 'poster-stat-punch') return posterStatPunch(spec)
  if (BEAUTIFUL_TEMPLATE_CONFIGS[spec.template_id]) return beautifulTemplate(spec, BEAUTIFUL_TEMPLATE_CONFIGS[spec.template_id])
  throw new Error(`unsupported template_id for Satori adapter: ${spec.template_id}`)
}
