import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'annotated-field-board'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'pin-and-paper',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/pin-and-paper-1.png'
}

function colors(spec) {
  return {
    paper: '#EDE66B',
    blue: '#1E4FDB',
    ink: '#1C2E33',
    muted: '#60684D'
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

function pin(theme, left, top, rotate = 0) {
  return box({ position: 'absolute', left, top, width: 120, height: 26, transform: `rotate(${rotate}deg)`, flexDirection: 'row', alignItems: 'center' }, [
    box({ width: 16, height: 16, borderRadius: 999, borderWidth: 2, borderColor: theme.blue }),
    box({ width: 86, height: 2, backgroundColor: theme.blue }),
    box({ width: 8, height: 8, borderRadius: 999, backgroundColor: theme.blue })
  ])
}

export function renderAnnotatedFieldBoard(spec) {
  const theme = colors(spec)
  const notes = list(spec, 'notes', ['For the team', 'You people can act'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.paper, overflow: 'hidden' }, [
    TextBlock(text(spec, 'eyebrow', 'A FIELD ISSUE · VOL. 1').toUpperCase(), {
      position: 'absolute',
      left: 66,
      top: 48,
      color: theme.blue,
      fontSize: 8,
      letterSpacing: 1.2,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    Title(text(spec, 'title', 'Kept\nthings'), {
      position: 'absolute',
      left: 96,
      top: 181,
      width: 330,
      color: theme.blue,
      fontSize: 60,
      lineHeight: 1.0,
      whiteSpace: 'pre-line',
      ...fontRole('display', spec, { fontWeight: 800 })
    }),
    TextBlock(notes[0] || 'For the team', {
      position: 'absolute',
      right: 94,
      top: 318,
      width: 166,
      color: theme.ink,
      fontSize: 15,
      lineHeight: 1.22,
      transform: 'rotate(-6deg)',
      ...fontRole('body', spec, { fontWeight: 700 })
    }),
    TextBlock((notes[1] || 'Surveyed all spring').toUpperCase(), {
      position: 'absolute',
      left: 98,
      bottom: 56,
      color: theme.muted,
      fontSize: 8,
      letterSpacing: 1,
      ...fontRole('metric', spec, { fontWeight: 600 })
    }),
    pin(theme, 772, 68, -10),
    pin(theme, 760, 338, 8),
    TextBlock('01 / 10', { position: 'absolute', right: 56, bottom: 39, color: theme.blue, fontSize: 8, ...fontRole('label', spec) })
  ])
}
