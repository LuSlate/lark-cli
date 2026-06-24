import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'pink-nocturne-feature'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'pink-script',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/pink-script-1.png'
}

function colors(spec) {
  return {
    black: '#100C12',
    pink: '#E63793',
    white: '#F5E8EC',
    muted: '#9C7A86'
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

export function renderPinkNocturneFeature(spec) {
  const theme = colors(spec)
  const sections = list(spec, 'sections', ['Edition', 'Director', 'Locale', 'Date'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.black, overflow: 'hidden' }, [
    box({ position: 'absolute', left: 210, top: 86, width: 540, height: 360, borderRadius: 999, backgroundColor: '#FFFFFF', opacity: 0.04 }),
    TextBlock(text(spec, 'eyebrow', 'MAISON NOCTURNE').toUpperCase(), {
      position: 'absolute',
      left: 34,
      top: 40,
      color: theme.pink,
      fontSize: 8,
      letterSpacing: 1.4,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    TextBlock('A FIELD REPORT ON LATE-NIGHT CULTURE', {
      position: 'absolute',
      left: 292,
      top: 82,
      color: theme.muted,
      fontSize: 8,
      letterSpacing: 2,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    Title(text(spec, 'title', 'After\nHours.'), {
      position: 'absolute',
      left: 336,
      top: 153,
      width: 340,
      color: theme.white,
      fontSize: 70,
      lineHeight: 0.93,
      whiteSpace: 'pre-line',
      ...fontRole('display', spec, { fontWeight: 800 })
    }),
    TextBlock(text(spec, 'quote', 'After'), {
      position: 'absolute',
      left: 336,
      top: 132,
      color: theme.pink,
      fontSize: 78,
      lineHeight: 0.9,
      ...fontRole('display', spec, { fontWeight: 800 })
    }),
    ...sections.slice(0, 4).map((item, index) =>
      TextBlock(item, {
        position: 'absolute',
        left: 33 + index * 235,
        bottom: 47,
        color: index === 3 ? theme.pink : theme.white,
        fontSize: 12,
        lineHeight: 1.1,
        ...fontRole('body', spec, { fontWeight: 700 })
      })
    ),
    TextBlock(text(spec, 'pageno', '01 / 09'), { position: 'absolute', right: 36, bottom: 23, color: theme.white, fontSize: 9, ...fontRole('metric', spec) })
  ])
}
