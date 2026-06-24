import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'retro-zine-spread'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'retro-zine',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/retro-zine-1.png'
}

function colors(spec) {
  return {
    paper: '#C9BDA2',
    green: '#00A66A',
    ink: '#202020',
    accent: '#F4F0E5'
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

export function renderRetroZineSpread(spec) {
  const theme = colors(spec)
  const notes = list(spec, 'notes', ['Never again', 'Always remember'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.paper, overflow: 'hidden' }, [
    TextBlock(text(spec, 'eyebrow', 'SMALL STORIES').toUpperCase(), { position: 'absolute', left: 372, top: 146, color: theme.green, fontSize: 9, letterSpacing: 1.1, ...fontRole('label', spec, { fontWeight: 800 }) }),
    Title(text(spec, 'title', 'NEXUS\nVENTURES').toUpperCase(), { position: 'absolute', left: 354, top: 170, width: 250, color: theme.green, fontSize: 45, lineHeight: 0.9, textAlign: 'center', ...fontRole('display', spec, { fontWeight: 900 }) }),
    box({ position: 'absolute', left: 438, top: 296, width: 52, height: 52, borderRadius: 999, backgroundColor: theme.ink, alignItems: 'center', justifyContent: 'center' }, [
      box({ width: 24, height: 24, borderRadius: 999, backgroundColor: theme.accent })
    ]),
    TextBlock(notes[0] || 'Never again', { position: 'absolute', left: 338, top: 345, width: 120, textAlign: 'right', color: theme.ink, fontSize: 7, ...fontRole('body', spec, { fontWeight: 600 }) }),
    TextBlock(notes[1] || 'Always remember', { position: 'absolute', left: 498, top: 345, width: 128, color: theme.ink, fontSize: 7, ...fontRole('body', spec, { fontWeight: 600 }) }),
    TextBlock(text(spec, 'stamp', '2026'), { position: 'absolute', left: 452, top: 382, color: theme.green, fontSize: 18, ...fontRole('metric', spec, { fontWeight: 900 }) }),
    TextBlock(text(spec, 'quote', 'Never again. Always remember.'), { position: 'absolute', left: 394, top: 356, width: 170, color: theme.ink, fontSize: 6, textAlign: 'center', ...fontRole('label', spec, { fontWeight: 700 }) })
  ])
}
