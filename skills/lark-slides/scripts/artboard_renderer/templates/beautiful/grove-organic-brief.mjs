import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'grove-organic-brief'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'grove',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/grove-1.png'
}

function colors(spec) {
  return {
    background: '#0D281A',
    title: '#F0E7D2',
    muted: '#A37745',
    faint: '#1A3A27'
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

export function renderGroveOrganicBrief(spec) {
  const theme = colors(spec)
  const metrics = list(spec, 'metrics', ['03', 'A calm year', 'Notes'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.background, overflow: 'hidden' }, [
    TextBlock(text(spec, 'eyebrow', 'GROVE NOTE / 2026').toUpperCase(), {
      position: 'absolute',
      left: 96,
      top: 133,
      color: theme.muted,
      fontSize: 8,
      letterSpacing: 1.4,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    Title(text(spec, 'title', '[Presentation Title\nGoes Here]'), {
      position: 'absolute',
      left: 96,
      top: 174,
      width: 438,
      color: theme.title,
      fontSize: 37,
      lineHeight: 1.02,
      ...fontRole('display', spec, { fontWeight: 400 })
    }),
    TextBlock(text(spec, 'subtitle', 'A year of craft by cadence or control'), {
      position: 'absolute',
      left: 98,
      top: 266,
      width: 310,
      color: theme.title,
      opacity: 0.72,
      fontSize: 10,
      lineHeight: 1.35,
      ...fontRole('body', spec, { fontWeight: 400 })
    }),
    TextBlock(metrics[0] || '03', {
      position: 'absolute',
      right: 75,
      bottom: 34,
      color: theme.faint,
      opacity: 0.35,
      fontSize: 87,
      lineHeight: 0.9,
      ...fontRole('metric', spec, { fontWeight: 300 })
    }),
    TextBlock((metrics[1] || 'Moment').toUpperCase(), {
      position: 'absolute',
      left: 96,
      bottom: 69,
      color: theme.muted,
      fontSize: 7,
      letterSpacing: 1.3,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    box({ position: 'absolute', left: 455, bottom: 34, width: 52, height: 2, backgroundColor: theme.title, opacity: 0.5 })
  ])
}
