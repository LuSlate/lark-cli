import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'creative-mode-grid'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'creative-mode',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/creative-mode-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    paper: source.background || '#EFE9D9',
    ink: source.text || '#101010',
    green: source.primary || '#1F8A4C',
    orange: source.accent || '#E85A1F',
    pink: source.pink || '#E966A6',
    blush: source.panel || '#F2C7D8'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function titleLines(value) {
  const words = value.toUpperCase().split(/\s+/).filter(Boolean)
  return {
    first: words.slice(0, 2).join(' ') || 'CREATIVE',
    second: words.slice(2).join(' ') || 'MODE'
  }
}

export function renderCreativeModeGrid(spec) {
  const theme = colors(spec)
  const title = titleLines(text(spec, 'title', 'CREATIVE MODE'))
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: 'hidden'
    },
    [
      box({ position: 'absolute', left: 48, top: 86, width: 30, height: 2, backgroundColor: theme.ink }),
      TextBlock('VOL. 01 / EDITION 2026', {
        position: 'absolute',
        left: 88,
        top: 82,
        color: theme.ink,
        fontSize: 14,
        letterSpacing: 6,
        ...fontRole('metric', spec, { fontWeight: 800 })
      }),
      Title(title.first, {
        position: 'absolute',
        left: 48,
        top: 200,
        width: 470,
        color: theme.ink,
        fontSize: 78,
        lineHeight: 0.9,
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      Title(title.second, {
        position: 'absolute',
        left: 48,
        top: 274,
        width: 370,
        color: theme.orange,
        fontSize: 78,
        lineHeight: 0.9,
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, 'subtitle', 'A presentation template - eight pages, eight layouts. Replace freely.'), {
        position: 'absolute',
        left: 48,
        top: 438,
        width: 430,
        color: '#2C2922',
        fontSize: 15,
        lineHeight: 1.35,
        ...fontRole('body', spec, { fontWeight: 500 })
      }),
      TextBlock(text(spec, 'eyebrow', 'A PRESENTATION TEMPLATE').toUpperCase(), {
        position: 'absolute',
        left: 32,
        bottom: 20,
        color: theme.ink,
        fontSize: 12,
        letterSpacing: 5,
        ...fontRole('label', spec, { fontWeight: 800 })
      }),
      box({ position: 'absolute', right: 48, top: 70, width: 384, height: 400, backgroundColor: theme.green, borderWidth: 2, borderColor: theme.ink }),
      box({ position: 'absolute', right: 82, top: 184, width: 198, height: 198, backgroundColor: theme.orange, borderWidth: 2, borderColor: theme.ink }),
      box({ position: 'absolute', right: 96, top: 174, width: 194, height: 194, backgroundColor: theme.pink, borderWidth: 2, borderColor: theme.ink }),
      box({ position: 'absolute', right: 132, top: 216, width: 124, height: 86, backgroundColor: theme.blush, borderWidth: 2, borderColor: theme.ink, transform: 'rotate(-7deg)' }),
      box({ position: 'absolute', right: 134, top: 294, width: 120, height: 17, backgroundColor: '#D24784', transform: 'rotate(-7deg)' }),
      TextBlock('01 * 08', {
        position: 'absolute',
        right: 32,
        bottom: 18,
        color: theme.ink,
        fontSize: 13,
        letterSpacing: 4,
        ...fontRole('metric', spec, { fontWeight: 900 })
      })
    ]
  )
}
