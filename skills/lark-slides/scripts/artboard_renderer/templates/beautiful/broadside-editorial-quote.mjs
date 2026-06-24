import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'editorial-quote-chart'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'broadside',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/broadside-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    orange: source.background || '#E85D26',
    black: source.text || '#111111',
    muted: source.muted || '#5E3526',
    cream: source.surface || '#F0ECE5'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function splitTitle(title) {
  const words = (title || 'this is the broadside style').toLowerCase().split(/\s+/).filter(Boolean)
  return {
    first: words.slice(0, 4).join(' ') || 'this is the',
    second: words.slice(4).join(' ') || 'broadside style'
  }
}

export function renderBroadsideEditorialQuote(spec) {
  const theme = colors(spec)
  const parts = splitTitle(text(spec, 'title', 'this is the broadside style'))
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.orange,
      color: theme.black,
      overflow: 'hidden'
    },
    [
      TextBlock(text(spec, 'page', '01'), {
        position: 'absolute',
        left: 54,
        top: 34,
        color: theme.muted,
        fontSize: 12,
        lineHeight: 1,
        ...fontRole('metric', spec, { fontWeight: 800 })
      }),
      TextBlock(text(spec, 'eyebrow', 'BROADSIDE').toUpperCase(), {
        position: 'absolute',
        right: 54,
        top: 34,
        width: 120,
        color: theme.muted,
        fontSize: 8,
        lineHeight: 1,
        textAlign: 'right',
        ...fontRole('label', spec, { fontWeight: 700 })
      }),
      Title(parts.first, {
        position: 'absolute',
        left: 54,
        top: 206,
        width: 820,
        color: theme.black,
        fontSize: 84,
        lineHeight: 0.78,
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      Title(parts.second, {
        position: 'absolute',
        left: 54,
        top: 318,
        width: 860,
        color: theme.black,
        fontSize: 84,
        lineHeight: 0.78,
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, 'subtitle', 'Protest poster meets publication cover. Type so large it becomes image.'), {
        position: 'absolute',
        left: 54,
        bottom: 74,
        width: 420,
        color: theme.muted,
        fontSize: 15,
        lineHeight: 1.55,
        ...fontRole('body', spec, { fontWeight: 500 })
      }),
      box({ position: 'absolute', left: 54, right: 54, bottom: 52, height: 1, backgroundColor: theme.muted, opacity: 0.45 }),
      TextBlock(text(spec, 'author', '[[Author Name]]'), {
        position: 'absolute',
        left: 54,
        bottom: 27,
        color: theme.muted,
        fontSize: 11,
        ...fontRole('label', spec, { fontWeight: 700 })
      }),
      TextBlock(text(spec, 'context', '[Year] · Context'), {
        position: 'absolute',
        right: 54,
        bottom: 27,
        width: 150,
        color: theme.muted,
        fontSize: 11,
        textAlign: 'right',
        ...fontRole('label', spec, { fontWeight: 700 })
      })
    ]
  )
}
