import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'vellum-scholar-brief'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'vellum',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/vellum-1.png'
}

function colors(spec) {
  return {
    navy: '#2A3870',
    yellow: '#F4E55C',
    muted: '#6D7BA5',
    paper: '#F8F5E8'
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

export function renderVellumScholarBrief(spec) {
  const theme = colors(spec)
  const stats = list(spec, 'stats', ['42 papers', '8 interviews', '3 scenarios'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.navy, overflow: 'hidden' }, [
    TextBlock(text(spec, 'eyebrow', 'POLICY BRIEF').toUpperCase(), { position: 'absolute', left: 386, top: 224, color: theme.muted, fontSize: 8, letterSpacing: 1.4, ...fontRole('label', spec, { fontWeight: 700 }) }),
    Title(text(spec, 'title', 'On Restraint'), { position: 'absolute', left: 119, top: 255, width: 540, color: theme.yellow, lineHeight: 1, ...fontRole('display', spec, { fontSize: 64, fontWeight: 400, textTransform: 'none' }) }),
    TextBlock(text(spec, 'subtitle', 'Field notes on the discipline of less.'), { position: 'absolute', left: 337, top: 326, width: 330, color: theme.muted, textAlign: 'center', lineHeight: 1.3, ...fontRole('body', spec, { fontSize: 11 }) }),
    TextBlock(stats.join(' · '), { position: 'absolute', left: 42, bottom: 32, color: theme.muted, ...fontRole('metric', spec, { fontSize: 8, fontWeight: 500 }) }),
    box({ position: 'absolute', left: 444, bottom: 20, width: 24, height: 2, backgroundColor: theme.paper, opacity: 0.7 }),
    TextBlock('01', { position: 'absolute', right: 36, bottom: 29, color: theme.muted, fontSize: 8, ...fontRole('label', spec) })
  ])
}
