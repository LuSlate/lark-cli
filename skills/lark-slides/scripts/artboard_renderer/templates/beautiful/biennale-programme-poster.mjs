import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'biennale-programme-poster'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'biennale-yellow',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/biennale-yellow-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    paper: source.background || '#E9E5DB',
    paperDeep: source.panel || '#DCD6C4',
    sun: source.primary || '#F1EE2E',
    haze: source.accent || '#F0DA7C',
    ink: source.text || '#1B2566'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function list(spec, key, fallback = []) {
  const value = spec.content?.[key]
  if (!Array.isArray(value)) return fallback
  const cleaned = value.filter((item) => typeof item === 'string' && item.trim()).map((item) => item.trim())
  return cleaned.length ? cleaned : fallback
}

function footerColumn(theme, spec, { left, width, heading, body }) {
  return box(
    {
      position: 'absolute',
      left,
      bottom: 18,
      width,
      flexDirection: 'column',
      borderTopWidth: 1,
      borderTopColor: theme.ink,
      paddingTop: 8
    },
    [
      TextBlock(heading.toUpperCase(), {
        color: theme.ink,
        fontSize: 7,
        lineHeight: 1,
        marginBottom: 7,
        ...fontRole('label', spec, { fontWeight: 800 })
      }),
      TextBlock(body, {
        color: theme.ink,
        fontSize: 7,
        lineHeight: 1.45,
        ...fontRole('body', spec, { fontWeight: 400 })
      })
    ]
  )
}

export function renderBiennaleProgrammePoster(spec) {
  const theme = colors(spec)
  const title = text(spec, 'title', 'Aurora Programme')
  const words = title.split(/\s+/)
  const first = words.slice(0, Math.max(1, Math.ceil(words.length / 2))).join(' ')
  const second = words.slice(Math.max(1, Math.ceil(words.length / 2))).join(' ') || 'Programme'
  const notes = list(spec, 'notes', [
    'Aurora Institute for Public Form',
    'Fourth annual open programme',
    'A field study of light, matter and atmosphere.',
    'Six months of exhibitions across three pavilions.'
  ])
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: 'hidden'
    },
    [
      box({ position: 'absolute', left: 0, top: 135, width: 960, height: 405, backgroundColor: theme.sun, opacity: 0.9 }),
      box({ position: 'absolute', right: 0, top: 0, width: 240, height: 132, backgroundColor: theme.haze, opacity: 0.62 }),
      box({ position: 'absolute', left: 720, top: 204, width: 240, height: 136, backgroundColor: theme.paper, opacity: 0.92 }),
      box({ position: 'absolute', left: 480, top: 338, width: 480, height: 135, backgroundColor: theme.paper, opacity: 0.72 }),
      TextBlock(text(spec, 'date', '02.05-\n11.10.2026'), {
        position: 'absolute',
        right: 36,
        top: 20,
        width: 280,
        color: theme.ink,
        fontSize: 43,
        lineHeight: 0.82,
        textAlign: 'right',
        whiteSpace: 'pre-line',
        ...fontRole('metric', spec, { fontWeight: 400 })
      }),
      Title(first, {
        position: 'absolute',
        left: 36,
        top: 166,
        width: 560,
        color: theme.ink,
        fontSize: 90,
        lineHeight: 0.85,
        ...fontRole('display', spec, { fontWeight: 400 })
      }),
      Title(second, {
        position: 'absolute',
        left: 36,
        top: 250,
        width: 580,
        color: theme.ink,
        fontSize: 90,
        lineHeight: 0.85,
        ...fontRole('display', spec, { fontWeight: 400 })
      }),
      TextBlock(text(spec, 'eyebrow', 'ANNUAL SURVEY · ISSUE NO. 04').toUpperCase(), {
        position: 'absolute',
        left: 38,
        bottom: 76,
        color: theme.ink,
        fontSize: 8,
        lineHeight: 1,
        ...fontRole('label', spec, { fontWeight: 800 })
      }),
      footerColumn(theme, spec, { left: 38, width: 164, heading: 'Hosted By', body: notes[0] || 'Aurora Institute' }),
      footerColumn(theme, spec, { left: 224, width: 150, heading: 'Edition', body: notes[1] || 'Fourth annual programme' }),
      footerColumn(theme, spec, { left: 395, width: 208, heading: 'Reading', body: notes[2] || 'A field study of light.' }),
      footerColumn(theme, spec, { left: 625, width: 296, heading: 'Notes', body: notes[3] || 'Six months of exhibitions and public lectures.' }),
      TextBlock(text(spec, 'page', '01 / 08'), {
        position: 'absolute',
        right: 24,
        bottom: 11,
        width: 58,
        color: theme.ink,
        fontSize: 8,
        textAlign: 'right',
        ...fontRole('metric', spec, { fontWeight: 500 })
      })
    ]
  )
}
