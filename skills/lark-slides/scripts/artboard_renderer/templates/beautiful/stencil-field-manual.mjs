import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'stencil-field-manual'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'stencil-tablet',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/stencil-tablet-1.png'
}

function colors(spec) {
  return {
    paper: '#EDE6D1',
    ink: '#141414',
    green: '#0E7F69',
    orange: '#FF6F2C'
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

export function renderStencilFieldManual(spec) {
  const theme = colors(spec)
  const principles = list(spec, 'principles', ['Archive', 'Method', 'Reading'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.paper, overflow: 'hidden' }, [
    TextBlock(text(spec, 'eyebrow', 'AGENCY NAME · PARTNER NAME').toUpperCase(), { position: 'absolute', left: 430, top: 34, color: theme.ink, fontSize: 8, letterSpacing: 1.2, ...fontRole('label', spec, { fontWeight: 900 }) }),
    Title(text(spec, 'title', 'BOLD BY\nDESIGN.').toUpperCase(), { position: 'absolute', left: 458, top: 292, width: 420, color: theme.ink, fontSize: 54, lineHeight: 0.87, ...fontRole('display', spec, { fontWeight: 900 }) }),
    box({ position: 'absolute', right: -34, top: 70, width: 132, height: 104, borderRadius: 999, backgroundColor: theme.green, transform: 'rotate(44deg)' }),
    box({ position: 'absolute', right: 24, top: 145, width: 116, height: 80, borderRadius: 999, backgroundColor: theme.green, transform: 'rotate(8deg)' }),
    box({ position: 'absolute', left: 462, bottom: 39, width: 90, height: 2, backgroundColor: theme.ink }),
    box({ position: 'absolute', left: 462, bottom: 34, width: 150, height: 2, backgroundColor: theme.ink, opacity: 0.45 }),
    box({ position: 'absolute', left: 462, bottom: 29, width: 112, height: 2, backgroundColor: theme.ink, opacity: 0.35 }),
    TextBlock(principles.slice(0, 2).join(' · ').toUpperCase(), { position: 'absolute', left: 472, bottom: 52, color: theme.ink, fontSize: 9, letterSpacing: 1, ...fontRole('body', spec, { fontWeight: 700 }) }),
    box({ position: 'absolute', left: 458, bottom: 52, width: 12, height: 12, backgroundColor: theme.orange }),
    TextBlock(text(spec, 'footer', '29 · IV · 2026'), { position: 'absolute', right: 47, bottom: 38, color: theme.ink, fontSize: 10, ...fontRole('metric', spec, { fontWeight: 700 }) })
  ])
}
