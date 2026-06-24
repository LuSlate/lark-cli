import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'trend-grid-report'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'cobalt-grid',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/cobalt-grid-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    paper: source.background || '#F0EBDE',
    cobalt: source.primary || '#1F2BE0',
    soft: source.muted || '#5560E5'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function graphGrid(theme) {
  const lines = []
  for (let x = 34; x < 930; x += 24) {
    lines.push(box({ position: 'absolute', left: x, top: 14, width: 1, height: 512, backgroundColor: theme.cobalt, opacity: 0.08 }))
  }
  for (let y = 14; y < 528; y += 24) {
    lines.push(box({ position: 'absolute', left: 34, top: y, width: 892, height: 1, backgroundColor: theme.cobalt, opacity: 0.08 }))
  }
  return lines
}

function glitch(theme) {
  const segments = []
  const slices = [
    { left: 742, top: 34, height: 58, bars: 10 },
    { left: 792, top: 84, height: 92, bars: 8 },
    { left: 704, top: 168, height: 146, bars: 12 },
    { left: 760, top: 306, height: 70, bars: 8 },
    { left: 720, top: 368, height: 122, bars: 12 },
    { left: 798, top: 482, height: 62, bars: 8 }
  ]
  slices.forEach(({ left, top, height, bars }) => {
    for (let i = 0; i < bars; i += 1) {
      segments.push(box({ position: 'absolute', left: left + i * 6, top, width: 3, height, backgroundColor: theme.cobalt }))
    }
  })
  return segments
}

export function renderTrendGridReport(spec) {
  const theme = colors(spec)
  const titleParts = text(spec, 'title', 'Index\n2026').split(/\n+/)
  return box(
    { width: 960, height: 540, position: 'relative', backgroundColor: theme.paper, color: theme.cobalt, overflow: 'hidden' },
    [
      ...graphGrid(theme),
      box({ position: 'absolute', left: 34, top: 14, width: 892, height: 1, backgroundColor: theme.cobalt }),
      box({ position: 'absolute', left: 34, bottom: 14, width: 892, height: 1, backgroundColor: theme.cobalt }),
      Title(titleParts[0] || 'Index', {
        position: 'absolute',
        left: 38,
        top: 112,
        width: 320,
        color: theme.cobalt,
        ...fontRole('display', spec, { fontWeight: 400 }),
        fontSize: 82,
        lineHeight: 1,
        textTransform: 'none'
      }),
      Title(titleParts[1] || '2026', {
        position: 'absolute',
        left: 38,
        top: 220,
        width: 320,
        color: theme.cobalt,
        ...fontRole('display', spec, { fontWeight: 400 }),
        fontSize: 82,
        lineHeight: 1,
        textTransform: 'none'
      }),
      TextBlock(text(spec, 'eyebrow', 'FIELD OFFICE QUARTERLY · VOLUME IV').toUpperCase(), {
        position: 'absolute',
        left: 34,
        top: 356,
        width: 340,
        color: theme.cobalt,
        ...fontRole('label', spec, { fontWeight: 900 }),
        fontSize: 9,
        lineHeight: 1,
      }),
      TextBlock(text(spec, 'subtitle', 'A field report on the state of things.'), {
        position: 'absolute',
        left: 34,
        top: 384,
        width: 470,
        color: theme.cobalt,
        ...fontRole('display', spec, { fontWeight: 400 }),
        fontSize: 18,
        lineHeight: 1.08,
        textTransform: 'none'
      }),
      ...glitch(theme),
      TextBlock(text(spec, 'vertical', 'issue.04  spring 2026  field-office.co'), {
        position: 'absolute',
        right: 26,
        top: 184,
        width: 12,
        color: theme.cobalt,
        ...fontRole('metric', spec, { fontWeight: 800 }),
        fontSize: 8,
        lineHeight: 1.2
      }),
      TextBlock(text(spec, 'footer_left', 'EDITED BY\nField Office Editorial · Lin Ito & Anya Mehrotra'), {
        position: 'absolute',
        left: 34,
        bottom: 46,
        width: 260,
        color: theme.cobalt,
        ...fontRole('metric', spec, { fontWeight: 700 }),
        fontSize: 8,
        whiteSpace: 'pre-wrap',
        lineHeight: 1.5
      }),
      TextBlock(text(spec, 'footer_right', 'DISTRIBUTED\nTo subscribers & the open web · twice a year'), {
        position: 'absolute',
        left: 216,
        bottom: 46,
        width: 300,
        color: theme.cobalt,
        ...fontRole('body', spec, { fontWeight: 700 }),
        fontSize: 8,
        whiteSpace: 'pre-wrap',
        lineHeight: 1.5
      }),
      TextBlock(text(spec, 'page', '01 / 08'), {
        position: 'absolute',
        right: 34,
        bottom: 30,
        color: theme.cobalt,
        ...fontRole('metric', spec, { fontWeight: 800 }),
        fontSize: 8,
      })
    ]
  )
}
