import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'playful-indie-launch'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'playful',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/playful-1.png'
}

function colors(spec) {
  return {
    peach: '#F2C69D',
    ink: '#171717',
    cream: '#F7DFB8',
    accent: '#111111'
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

export function renderPlayfulIndieLaunch(spec) {
  const theme = colors(spec)
  const stats = list(spec, 'stats', ['02-05-26', 'Special drop', 'No. 4'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.peach, overflow: 'hidden' }, [
    Title(stats[0] || '02-05-26', {
      position: 'absolute',
      left: 92,
      top: 200,
      width: 330,
      color: theme.ink,
      fontSize: 53,
      lineHeight: 0.92,
      ...fontRole('metric', spec, { fontWeight: 900 })
    }),
    Title(text(spec, 'title', 'Creative Direction & Visual\nSystem'), {
      position: 'absolute',
      left: 92,
      top: 267,
      width: 380,
      color: theme.ink,
      fontSize: 29,
      lineHeight: 1.02,
      ...fontRole('display', spec, { fontWeight: 900 })
    }),
    TextBlock(text(spec, 'subtitle', 'A generous presentation for early-stage launches.'), {
      position: 'absolute',
      left: 96,
      top: 336,
      width: 285,
      color: theme.ink,
      fontSize: 10,
      lineHeight: 1.25,
      ...fontRole('body', spec, { fontWeight: 500 })
    }),
    box({ position: 'absolute', right: 148, top: 136, width: 74, height: 104, borderRadius: 999, borderWidth: 2, borderColor: theme.ink, transform: 'rotate(10deg)', alignItems: 'center', justifyContent: 'center' }, [
      box({ width: 44, height: 65, borderRadius: 999, backgroundColor: theme.ink, transform: 'rotate(12deg)' })
    ]),
    box({ position: 'absolute', right: 242, bottom: 84, width: 54, height: 70, borderRadius: 999, borderWidth: 2, borderColor: theme.ink, transform: 'rotate(14deg)' }),
    TextBlock(text(spec, 'eyebrow', 'SPECIAL DROP').toUpperCase(), {
      position: 'absolute',
      right: 129,
      top: 256,
      color: theme.ink,
      fontSize: 8,
      letterSpacing: 1.4,
      transform: 'rotate(90deg)',
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    TextBlock(stats[1] || 'Special drop', { position: 'absolute', right: 38, bottom: 24, color: theme.ink, fontSize: 8, ...fontRole('label', spec) })
  ])
}
