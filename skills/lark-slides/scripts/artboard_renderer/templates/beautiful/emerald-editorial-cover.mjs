import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'emerald-editorial-cover'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'emerald-editorial',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/emerald-editorial-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    emerald: source.background || '#3CD896',
    navy: source.text || '#0F1A5C',
    paper: source.panel || '#F1E9D6'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function coverWords(title) {
  const words = title.toUpperCase().split(/\s+/).filter(Boolean)
  if (words.length >= 4) {
    return {
      top: words.slice(0, 2).join(' '),
      bottom: words.slice(2).join(' ')
    }
  }
  return { top: 'STATE', bottom: 'THE WORK AHEAD' }
}

export function renderEmeraldEditorialCover(spec) {
  const theme = colors(spec)
  const words = coverWords(text(spec, 'title', 'The State of the Work Ahead'))
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.emerald,
      color: theme.navy,
      overflow: 'hidden'
    },
    [
      TextBlock('The', {
        position: 'absolute',
        left: 440,
        top: 79,
        width: 88,
        color: theme.navy,
        fontSize: 42,
        lineHeight: 0.9,
        textAlign: 'center',
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      Title(words.top, {
        position: 'absolute',
        left: 260,
        top: 120,
        width: 440,
        color: theme.navy,
        fontSize: 86,
        lineHeight: 0.9,
        textAlign: 'center',
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      box({ position: 'absolute', left: 130, top: 216, width: 314, height: 3, backgroundColor: theme.navy }),
      box({ position: 'absolute', left: 130, top: 223, width: 314, height: 3, backgroundColor: theme.navy }),
      TextBlock('of', {
        position: 'absolute',
        left: 454,
        top: 208,
        width: 52,
        color: theme.navy,
        fontSize: 40,
        lineHeight: 1,
        textAlign: 'center',
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      box({ position: 'absolute', right: 130, top: 216, width: 314, height: 3, backgroundColor: theme.navy }),
      box({ position: 'absolute', right: 130, top: 223, width: 314, height: 3, backgroundColor: theme.navy }),
      Title(words.bottom, {
        position: 'absolute',
        left: 200,
        top: 246,
        width: 560,
        color: theme.navy,
        fontSize: 70,
        lineHeight: 0.92,
        textAlign: 'center',
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, 'subtitle', 'A presentation for the leadership team').toUpperCase(), {
        position: 'absolute',
        left: 280,
        top: 430,
        width: 400,
        color: theme.navy,
        fontSize: 14,
        letterSpacing: 5,
        textAlign: 'center',
        ...fontRole('body', spec, { fontWeight: 900 })
      }),
      TextBlock('PREPARED BY THE PLANNING OFFICE', {
        position: 'absolute',
        left: 56,
        bottom: 32,
        color: theme.navy,
        fontSize: 14,
        ...fontRole('label', spec, { fontWeight: 900 })
      }),
      TextBlock('NOVEMBER · MMXXV', {
        position: 'absolute',
        right: 56,
        bottom: 32,
        color: theme.navy,
        fontSize: 14,
        textAlign: 'right',
        ...fontRole('metric', spec, { fontWeight: 900 })
      })
    ]
  )
}
