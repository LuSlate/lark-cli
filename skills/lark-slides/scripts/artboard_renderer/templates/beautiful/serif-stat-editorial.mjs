import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'serif-stat-editorial'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'editorial-forest',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/editorial-forest-1.png'
}

function colors(spec) {
  return {
    background: '#244A2E',
    text: '#ECA0B5',
    muted: '#E7D8BE',
    line: '#ECA0B5'
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

export function renderSerifStatEditorial(spec) {
  const theme = colors(spec)
  const cards = list(spec, 'cards', ['Studio placeholder', 'Presented by name', 'Review note'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.background, overflow: 'hidden' }, [
    TextBlock(text(spec, 'eyebrow', 'A PRESENTATION TEMPLATE').toUpperCase(), {
      position: 'absolute',
      left: 66,
      top: 39,
      color: theme.muted,
      fontSize: 7,
      letterSpacing: 1.4,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    box({
      position: 'absolute',
      right: 96,
      top: 34,
      width: 34,
      height: 34,
      borderRadius: 999,
      borderWidth: 1,
      borderColor: theme.line,
      alignItems: 'center',
      justifyContent: 'center'
    }, [
      TextBlock('01', { color: theme.muted, fontSize: 7, ...fontRole('metric', spec, { fontWeight: 400 }) })
    ]),
    Title(text(spec, 'title', 'Quarterly\nReview\n2026'), {
      position: 'absolute',
      left: 70,
      top: 116,
      width: 386,
      color: theme.text,
      fontSize: 64,
      lineHeight: 0.92,
      whiteSpace: 'pre-line',
      ...fontRole('display', spec, { fontWeight: 400, letterSpacing: -0.5 })
    }),
    TextBlock(text(spec, 'subtitle', cards[0] || 'Studio placeholder').toUpperCase(), {
      position: 'absolute',
      left: 70,
      bottom: 72,
      color: theme.text,
      fontSize: 8,
      letterSpacing: 1.2,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    TextBlock((cards[1] || 'Presented by name').toUpperCase(), {
      position: 'absolute',
      right: 86,
      bottom: 72,
      color: theme.text,
      fontSize: 8,
      letterSpacing: 1.2,
      ...fontRole('body', spec, { fontWeight: 700 })
    }),
    box({ position: 'absolute', left: 69, bottom: 55, width: 160, height: 1, backgroundColor: theme.text, opacity: 0.55 }),
    box({ position: 'absolute', right: 83, bottom: 55, width: 160, height: 1, backgroundColor: theme.text, opacity: 0.55 })
  ])
}
