import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'mat-midcentury-board'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'mat',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/mat-1.png'
}

function colors(spec) {
  return {
    background: '#232E26',
    cream: '#EDE6D0',
    paper: '#F5EDD8',
    ink: '#121D17',
    accent: '#D47B3B'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function list(spec, key, fallback = []) {
  const value = spec.content?.[key]
  return Array.isArray(value) && value.length ? value : fallback
}

export function renderMatMidcenturyBoard(spec) {
  const theme = colors(spec)
  const cards = list(spec, 'cards', ['Designed by Studio', 'The precision studio tools that work alone.'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.background, overflow: 'hidden' }, [
    TextBlock(text(spec, 'eyebrow', 'STUDIO NOTE').toUpperCase(), {
      position: 'absolute',
      left: 598,
      top: 26,
      color: theme.accent,
      fontSize: 7,
      letterSpacing: 1.1,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    Title(text(spec, 'title', 'Craft\nMatters'), {
      position: 'absolute',
      left: 55,
      top: 45,
      width: 310,
      color: theme.cream,
      lineHeight: 0.93,
      whiteSpace: 'pre-line',
      ...fontRole('display', spec, { fontSize: 72, fontWeight: 900, textTransform: 'none' })
    }),
    TextBlock(text(spec, 'subtitle', 'Designed for the hands that build things.'), {
      position: 'absolute',
      left: 755,
      top: 112,
      width: 140,
      color: theme.cream,
      opacity: 0.68,
      lineHeight: 1.35,
      ...fontRole('body', spec, { fontSize: 9, fontWeight: 400 })
    }),
    box({ position: 'absolute', left: 744, top: 167, width: 84, height: 1, backgroundColor: theme.cream, opacity: 0.32 }),
    box({ position: 'absolute', left: 744, top: 175, width: 126, height: 1, backgroundColor: theme.cream, opacity: 0.22 }),
    box({ position: 'absolute', left: 744, top: 183, width: 58, height: 1, backgroundColor: theme.cream, opacity: 0.22 }),
    box({ position: 'absolute', left: 60, top: 280, width: 185, height: 104, backgroundColor: theme.paper, padding: 16, flexDirection: 'column' }, [
      TextBlock(cards[0] || 'Designed by', { color: theme.ink, lineHeight: 1.05, ...fontRole('label', spec, { fontSize: 14, fontWeight: 800 }) }),
      TextBlock(cards[1] || 'Studio tools', { color: theme.ink, marginTop: 8, lineHeight: 1.25, ...fontRole('body', spec, { fontSize: 10, fontWeight: 600 }) })
    ]),
    TextBlock('MAT / 2026', {
      position: 'absolute',
      right: 38,
      bottom: 23,
      color: theme.cream,
      opacity: 0.72,
      letterSpacing: 1,
      ...fontRole('metric', spec, { fontSize: 7, fontWeight: 500 })
    }),
    box({ position: 'absolute', left: 448, bottom: 22, width: 4, height: 2, backgroundColor: theme.cream, opacity: 0.7 }),
    box({ position: 'absolute', left: 458, bottom: 22, width: 24, height: 2, backgroundColor: theme.cream, opacity: 0.45 }),
    box({ position: 'absolute', left: 488, bottom: 22, width: 4, height: 2, backgroundColor: theme.cream, opacity: 0.7 }),
    box({ position: 'absolute', right: 32, bottom: 38, width: 3, height: 3, backgroundColor: theme.cream, opacity: 0.5 }),
    box({ position: 'absolute', right: 45, bottom: 38, width: 3, height: 3, backgroundColor: theme.cream, opacity: 0.5 }),
    box({ position: 'absolute', right: 58, bottom: 38, width: 3, height: 3, backgroundColor: theme.cream, opacity: 0.5 })
  ])
}
