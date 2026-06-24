import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'sticky-workshop-board'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'scatterbrain',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/scatterbrain-1.png'
}

function colors(spec) {
  return {
    paper: '#D9C9AD',
    yellow: '#F8D444',
    blue: '#9DC7E8',
    green: '#BDE083',
    ink: '#1C1C1C'
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

function note(item, style, spec) {
  return box({ position: 'absolute', width: 156, height: 66, padding: 9, transform: style.transform, backgroundColor: style.color, left: style.left, top: style.top, justifyContent: 'center', alignItems: 'center' }, [
    TextBlock(item, { color: '#111111', fontSize: 16, lineHeight: 1, textAlign: 'center', ...fontRole('label', spec, { fontWeight: 800 }) })
  ])
}

export function renderStickyWorkshopBoard(spec) {
  const theme = colors(spec)
  const postits = list(spec, 'postits', ['Workshop map', 'Ask a good question', 'Prototype fast'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.paper, overflow: 'hidden' }, [
    note(postits[1] || 'User pain', { left: 322, top: 176, color: theme.green, transform: 'rotate(-8deg)' }, spec),
    note(text(spec, 'title', postits[0] || 'Workshop map'), { left: 407, top: 164, color: theme.yellow, transform: 'rotate(2deg)' }, spec),
    note(postits[2] || 'Launch test', { left: 517, top: 142, color: theme.blue, transform: 'rotate(8deg)' }, spec),
    TextBlock(text(spec, 'title', postits[0] || 'Workshop map'), {
      position: 'absolute',
      left: 423,
      top: 188,
      width: 126,
      color: theme.ink,
      fontSize: 18,
      lineHeight: 1,
      textAlign: 'center',
      transform: 'rotate(2deg)',
      ...fontRole('display', spec, { fontWeight: 900 })
    }),
    TextBlock(text(spec, 'eyebrow', 'BRAINSTORM BOARD').toUpperCase(), { position: 'absolute', left: 389, top: 285, color: theme.ink, fontSize: 8, letterSpacing: 1.1, ...fontRole('label', spec, { fontWeight: 700 }) }),
    TextBlock(text(spec, 'subtitle', 'Collect your thoughts, pin them down, and make the big problem small.'), { position: 'absolute', left: 348, top: 306, width: 266, color: theme.ink, fontSize: 9, lineHeight: 1.4, textAlign: 'center', ...fontRole('body', spec) }),
    TextBlock(String(postits.length).padStart(2, '0'), { position: 'absolute', right: 30, bottom: 22, color: theme.ink, fontSize: 8, ...fontRole('metric', spec) })
  ])
}
