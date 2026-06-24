import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'executive-dashboard'

const PAGE_VARIANTS = ['cover', 'agenda', 'metrics', 'dashboard', 'split', 'bars', 'quote', 'timeline', 'detail', 'closing']

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'production',
  renderer_stage: 'closed_loop_sample',
  default_selectable: true,
  selection_scope: 'production',
  source_family: 'blue-professional',
  page_family: {
    family_id: 'blue-professional',
    supported_page_variants: PAGE_VARIANTS,
    variant_usage_policy: {
      singletons: ['cover', 'agenda', 'closing'],
      repeatable: ['metrics', 'dashboard', 'split', 'bars', 'quote', 'timeline', 'detail']
    }
  },
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/blue-professional-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    background: source.background || '#FDFAE7',
    panel: source.panel || '#FFFFFF',
    surface: source.surface || '#F5F7FF',
    primary: source.primary || '#1E2BFA',
    accent: source.accent || '#1E2BFA',
    text: source.text || '#111111',
    muted: source.muted || '#6B6B6B',
    border: source.border || '#D4D8FE'
  }
}

const FONT_ROLE_RESOLVERS = {
  display: (spec) => fontRole('display', spec),
  body: (spec) => fontRole('body', spec),
  label: (spec) => fontRole('label', spec),
  metric: (spec) => fontRole('metric', spec)
}

function role(roleName, spec, style = {}) {
  const resolver = FONT_ROLE_RESOLVERS[roleName] || ((input) => fontRole(roleName, input))
  return { ...resolver(spec), ...style }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function list(spec, keys, fallback = []) {
  for (const key of keys) {
    const value = spec.content?.[key]
    if (Array.isArray(value)) {
      const cleaned = value.filter((item) => typeof item === 'string' && item.trim()).map((item) => item.trim())
      if (cleaned.length) return cleaned
    }
  }
  return fallback
}

function metricList(spec) {
  const raw = spec.content?.metrics
  if (Array.isArray(raw) && raw.length) return raw
  return ['+18% Revenue', '4 Regions', '92 NPS', '3 Priorities']
}

function variantId(spec) {
  const raw = spec.page_variant_id || spec.page_role || 'dashboard'
  const normalized = String(raw).toLowerCase().replace(/^data_/, '').replace(/^process_or_/, '')
  if (normalized === 'toc') return 'agenda'
  if (normalized === 'timeline') return 'timeline'
  if (PAGE_VARIANTS.includes(normalized)) return normalized
  throw new Error(`unsupported page_variant_id for executive-dashboard: ${raw}`)
}

function shell(spec, variant, children = []) {
  const theme = colors(spec)
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.background,
      color: theme.text,
      overflow: 'hidden'
    },
    [
      box({ position: 'absolute', left: 0, top: 0, width: 960, height: 540, backgroundColor: theme.background }),
      box({ position: 'absolute', left: 0, bottom: 0, width: 96, height: 2, backgroundColor: theme.primary }),
      TextBlock(String(variant || '').toUpperCase(), {
        position: 'absolute',
        right: 48,
        top: 30,
        color: theme.primary,
        fontSize: 10,
        letterSpacing: 1,
        ...role('label', spec, { fontSize: 10, lineHeight: 1 })
      }),
      TextBlock(text(spec, 'footer', 'Q2 2026 · Confidential'), {
        position: 'absolute',
        left: 48,
        bottom: 22,
        width: 260,
        color: theme.muted,
        ...role('label', spec, { fontSize: 8, lineHeight: 1 })
      }),
      ...children
    ]
  )
}

function titleBlock(spec, top = 74, width = 560) {
  const theme = colors(spec)
  return [
    TextBlock(text(spec, 'eyebrow', 'EXECUTIVE REVIEW').toUpperCase(), {
      position: 'absolute',
      left: 56,
      top,
      color: theme.primary,
      letterSpacing: 1.4,
      ...role('label', spec, { fontSize: 11, lineHeight: 1 })
    }),
    Title(text(spec, 'title', 'Market Outlook'), {
      position: 'absolute',
      left: 56,
      top: top + 26,
      width,
      color: theme.text,
      ...role('display', spec, { fontSize: 42, lineHeight: 1, fontWeight: 900 })
    }),
    TextBlock(text(spec, 'subtitle', 'An analytical overview of priorities, evidence, and operating decisions.'), {
      position: 'absolute',
      left: 58,
      top: top + 90,
      width: Math.min(width + 80, 610),
      color: theme.muted,
      ...role('body', spec, { fontSize: 13, lineHeight: 1.35 })
    })
  ]
}

function numberLabel(spec, value, style = {}) {
  const theme = colors(spec)
  return TextBlock(String(value).padStart(2, '0'), {
    color: theme.primary,
    ...role('label', spec, { fontSize: 13, fontWeight: 900, lineHeight: 1 }),
    ...style
  })
}

function renderCover(spec) {
  const theme = colors(spec)
  return shell(spec, 'cover', [
    box({
      position: 'absolute',
      right: -86,
      top: -56,
      width: 374,
      height: 660,
      backgroundColor: '#E8E7E6',
      transform: 'skewX(-10deg)'
    }),
    box({ position: 'absolute', left: 77, top: 183, width: 30, height: 2, backgroundColor: theme.primary }),
    TextBlock(text(spec, 'eyebrow', 'EXECUTIVE REVIEW').toUpperCase(), {
      position: 'absolute',
      left: 78,
      top: 168,
      color: theme.primary,
      letterSpacing: 1.5,
      ...role('label', spec, { fontSize: 10, fontWeight: 900, lineHeight: 1 })
    }),
    Title(text(spec, 'title', '内部业务复盘'), {
      position: 'absolute',
      left: 77,
      top: 199,
      width: 420,
      color: theme.text,
      ...role('display', spec, { fontSize: 38, lineHeight: 1.08, fontWeight: 900 })
    }),
    TextBlock(text(spec, 'subtitle', '指标、证据与行动计划'), {
      position: 'absolute',
      left: 78,
      top: 282,
      width: 440,
      color: theme.muted,
      ...role('body', spec, { fontSize: 12, lineHeight: 1.35 })
    }),
    box({ position: 'absolute', right: 77, bottom: 63, width: 30, height: 30, flexDirection: 'row', flexWrap: 'wrap', gap: 5 },
      Array.from({ length: 9 }).map(() => box({ width: 3, height: 3, backgroundColor: theme.primary, opacity: 0.28 }))
    ),
    TextBlock('1 / 10', {
      position: 'absolute',
      left: 28,
      bottom: 14,
      width: 48,
      color: theme.muted,
      ...role('label', spec, { fontSize: 7, lineHeight: 1 })
    })
  ])
}

function renderAgenda(spec) {
  const theme = colors(spec)
  const items = list(spec, ['agenda', 'points', 'takeaways'], ['Context', 'Signals', 'Risks', 'Decisions', 'Next actions']).slice(0, 5)
  return shell(spec, 'agenda', [
    ...titleBlock(spec, 54, 420),
    box({ position: 'absolute', right: 62, top: 92, width: 356, height: 360, backgroundColor: theme.panel, border: `1px solid ${theme.border}`, padding: 28, flexDirection: 'column' },
      items.map((item, index) =>
        box({ flexDirection: 'row', alignItems: 'center', height: 58, borderBottom: index === items.length - 1 ? '0px solid transparent' : `1px solid ${theme.border}` }, [
          numberLabel(spec, index + 1, { width: 42 }),
          TextBlock(item, { width: 250, color: theme.text, ...role('body', spec, { fontSize: 18, lineHeight: 1.1, fontWeight: 700 }) })
        ])
      )
    )
  ])
}

function renderMetrics(spec) {
  const theme = colors(spec)
  const metrics = metricList(spec).slice(0, 4)
  return shell(spec, 'metrics', [
    ...titleBlock(spec, 46, 540),
    box({ position: 'absolute', left: 58, top: 238, width: 844, height: 190, flexDirection: 'row', gap: 18 },
      metrics.map((item, index) =>
        box({ width: 197, height: 172, backgroundColor: index === 0 ? theme.primary : theme.panel, border: `1px solid ${index === 0 ? theme.primary : theme.border}`, padding: 18, flexDirection: 'column', justifyContent: 'space-between' }, [
          numberLabel(spec, index + 1, { color: index === 0 ? theme.panel : theme.primary }),
          TextBlock(String(item).split(' ')[0], { color: index === 0 ? theme.panel : theme.text, ...role('metric', spec, { fontSize: 34, lineHeight: 0.95, fontWeight: 900 }) }),
          TextBlock(String(item).split(' ').slice(1).join(' ') || `Metric ${index + 1}`, { color: index === 0 ? theme.panel : theme.muted, ...role('label', spec, { fontSize: 10, lineHeight: 1.2 }) })
        ])
      )
    )
  ])
}

function renderDashboard(spec) {
  const theme = colors(spec)
  const metrics = metricList(spec).slice(0, 3)
  return shell(spec, 'dashboard', [
    ...titleBlock(spec, 40, 440),
    box({ position: 'absolute', left: 56, bottom: 84, width: 492, height: 176, backgroundColor: theme.panel, border: `1px solid ${theme.border}`, padding: 22, flexDirection: 'column' }, [
      TextBlock('PERFORMANCE MIX', { color: theme.primary, ...role('label', spec, { fontSize: 10, letterSpacing: 1.1 }) }),
      box({ marginTop: 22, width: 430, height: 84, flexDirection: 'row', alignItems: 'flex-end', gap: 17 },
        [86, 112, 64, 136, 102, 156, 119].map((height) => box({ width: 44, height, backgroundColor: theme.primary, opacity: height > 120 ? 1 : 0.36 }))
      )
    ]),
    box({ position: 'absolute', right: 60, top: 88, width: 290, height: 342, flexDirection: 'column', gap: 14 },
      metrics.map((item, index) =>
        box({ height: 104, backgroundColor: theme.surface, border: `1px solid ${theme.border}`, padding: 18, flexDirection: 'column' }, [
          TextBlock(String(item), { color: theme.text, ...role('body', spec, { fontSize: 17, lineHeight: 1.15, fontWeight: 700 }) }),
          box({ marginTop: 14, width: 210 - index * 28, height: 5, backgroundColor: theme.primary })
        ])
      )
    )
  ])
}

function renderSplit(spec) {
  const theme = colors(spec)
  const left = list(spec, ['left_points', 'points'], ['What is working', 'Signal quality improved', 'Execution rhythm stabilized']).slice(0, 3)
  const right = list(spec, ['right_points', 'risks'], ['What needs focus', 'Funnel conversion gap', 'Ownership across teams']).slice(0, 3)
  const panel = (items, side, x) =>
    box({ position: 'absolute', left: x, top: 176, width: 390, height: 244, backgroundColor: side === 'left' ? theme.panel : theme.surface, border: `1px solid ${theme.border}`, padding: 24, flexDirection: 'column' }, [
      TextBlock(side === 'left' ? 'LEFT TRACK' : 'RIGHT TRACK', { color: theme.primary, ...role('label', spec, { fontSize: 10, letterSpacing: 1.2 }) }),
      ...items.map((item, index) =>
        box({ marginTop: index === 0 ? 22 : 14, flexDirection: 'row' }, [
          box({ width: 7, height: 7, marginTop: 7, marginRight: 12, backgroundColor: theme.primary }),
          TextBlock(item, { width: 285, color: theme.text, ...role('body', spec, { fontSize: 16, lineHeight: 1.25 }) })
        ])
      )
    ])
  return shell(spec, 'split', [...titleBlock(spec, 44, 620), panel(left, 'left', 56), panel(right, 'right', 514)])
}

function renderBars(spec) {
  const theme = colors(spec)
  const items = list(spec, ['bars', 'metrics'], ['North 78', 'South 64', 'East 91', 'West 58', 'Central 73']).slice(0, 5)
  return shell(spec, 'bars', [
    ...titleBlock(spec, 42, 520),
    box({ position: 'absolute', left: 86, top: 210, width: 780, height: 230, flexDirection: 'column', gap: 15 },
      items.map((item, index) => {
        const width = [610, 480, 690, 420, 545][index] || 500
        return box({ height: 30, flexDirection: 'row', alignItems: 'center' }, [
          TextBlock(String(item).replace(/\s+\d+$/, ''), { width: 150, color: theme.text, ...role('label', spec, { fontSize: 11, lineHeight: 1 }) }),
          box({ width, height: 18, backgroundColor: theme.primary, opacity: index === 2 ? 1 : 0.52 }),
          TextBlock(String(item).match(/\d+/)?.[0] || String(70 + index), { marginLeft: 15, color: theme.primary, ...role('metric', spec, { fontSize: 18, lineHeight: 1, fontWeight: 900 }) })
        ])
      })
    )
  ])
}

function renderQuote(spec) {
  const theme = colors(spec)
  return shell(spec, 'quote', [
    TextBlock('“', { position: 'absolute', left: 66, top: 60, color: theme.primary, opacity: 0.18, ...role('display', spec, { fontSize: 170, lineHeight: 0.8, fontWeight: 900 }) }),
    Title(text(spec, 'quote', text(spec, 'title', 'The review is only useful when every claim can be traced to a decision.')), {
      position: 'absolute',
      left: 128,
      top: 126,
      width: 650,
      color: theme.text,
      ...role('display', spec, { fontSize: 34, lineHeight: 1.08, fontWeight: 900 })
    }),
    TextBlock(text(spec, 'author', 'SVGlide Operating Review'), { position: 'absolute', left: 132, top: 346, color: theme.primary, ...role('label', spec, { fontSize: 12, letterSpacing: 1.4 }) }),
    box({ position: 'absolute', right: 78, top: 92, width: 92, height: 332, border: `2px solid ${theme.primary}` })
  ])
}

function renderTimeline(spec) {
  const theme = colors(spec)
  const items = list(spec, ['timeline', 'points'], ['Discover', 'Prioritize', 'Build', 'Launch', 'Review']).slice(0, 5)
  return shell(spec, 'timeline', [
    ...titleBlock(spec, 42, 520),
    box({ position: 'absolute', left: 88, top: 268, width: 760, height: 4, backgroundColor: theme.border }),
    ...items.map((item, index) => {
      const x = 88 + index * 175
      return box({ position: 'absolute', left: x, top: 226, width: 118, height: 122, flexDirection: 'column', alignItems: 'flex-start' }, [
        box({ width: 34, height: 34, borderRadius: 17, backgroundColor: theme.primary, marginBottom: 18 }),
        numberLabel(spec, index + 1, { marginBottom: 10 }),
        TextBlock(item, { width: 116, color: theme.text, ...role('body', spec, { fontSize: 14, fontWeight: 700, lineHeight: 1.15 }) })
      ])
    })
  ])
}

function renderDetail(spec) {
  const theme = colors(spec)
  const points = list(spec, ['details', 'points'], ['Observation: demand is resilient but uneven by segment.', 'Evidence: high-intent cohorts continue to expand.', 'Decision: focus resources on measurable conversion lift.']).slice(0, 3)
  return shell(spec, 'detail', [
    box({ position: 'absolute', left: 54, top: 54, width: 852, height: 388, backgroundColor: theme.panel, border: `1px solid ${theme.border}` }),
    TextBlock(text(spec, 'eyebrow', 'DETAIL NOTE').toUpperCase(), { position: 'absolute', left: 92, top: 92, color: theme.primary, ...role('label', spec, { fontSize: 10, letterSpacing: 1.2 }) }),
    Title(text(spec, 'title', 'Decision evidence'), { position: 'absolute', left: 92, top: 126, width: 330, color: theme.text, ...role('display', spec, { fontSize: 34, lineHeight: 1.04, fontWeight: 900 }) }),
    box({ position: 'absolute', left: 488, top: 92, width: 340, height: 300, flexDirection: 'column', gap: 18 },
      points.map((item, index) =>
        box({ minHeight: 70, borderBottom: `1px solid ${theme.border}`, flexDirection: 'row' }, [
          numberLabel(spec, index + 1, { width: 44 }),
          TextBlock(item, { width: 280, color: theme.text, ...role('body', spec, { fontSize: 15, lineHeight: 1.3 }) })
        ])
      )
    )
  ])
}

function renderClosing(spec) {
  const theme = colors(spec)
  const items = list(spec, ['takeaways', 'points'], ['Keep the decision log short', 'Tie every metric to one owner', 'Review progress in the next operating cycle']).slice(0, 3)
  return shell(spec, 'closing', [
    box({ position: 'absolute', left: 64, top: 74, width: 832, height: 300, backgroundColor: theme.primary, padding: 42, flexDirection: 'column', justifyContent: 'center' }, [
      TextBlock(text(spec, 'eyebrow', 'NEXT ACTIONS').toUpperCase(), { color: theme.panel, opacity: 0.78, marginBottom: 22, ...role('label', spec, { fontSize: 11, letterSpacing: 1.4 }) }),
      Title(text(spec, 'title', 'From review to execution'), { width: 650, color: theme.panel, ...role('display', spec, { fontSize: 44, lineHeight: 1, fontWeight: 900 }) })
    ]),
    box({ position: 'absolute', left: 104, top: 400, width: 742, height: 68, flexDirection: 'row', gap: 20 },
      items.map((item, index) =>
        box({ width: 230, flexDirection: 'row' }, [
          numberLabel(spec, index + 1, { width: 36 }),
          TextBlock(item, { width: 178, color: theme.text, ...role('body', spec, { fontSize: 13, lineHeight: 1.22, fontWeight: 700 }) })
        ])
      )
    )
  ])
}

export function renderExecutiveDashboard(spec) {
  const variant = variantId(spec)
  switch (variant) {
    case 'cover':
      return renderCover(spec)
    case 'agenda':
      return renderAgenda(spec)
    case 'metrics':
      return renderMetrics(spec)
    case 'dashboard':
      return renderDashboard(spec)
    case 'split':
      return renderSplit(spec)
    case 'bars':
      return renderBars(spec)
    case 'quote':
      return renderQuote(spec)
    case 'timeline':
      return renderTimeline(spec)
    case 'detail':
      return renderDetail(spec)
    case 'closing':
      return renderClosing(spec)
    default:
      throw new Error(`unsupported page_variant_id for executive-dashboard: ${spec.page_variant_id}`)
  }
}
