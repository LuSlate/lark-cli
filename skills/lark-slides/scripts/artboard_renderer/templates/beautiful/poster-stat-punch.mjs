import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'poster-stat-punch'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'bold-poster',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/bold-poster-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    background: source.background || '#FFFFFF',
    paper: source.surface || '#F5F2EF',
    text: source.text || '#1C1410',
    muted: source.muted || '#7B706A',
    red: source.primary || '#D8000F',
    line: source.accent || '#1C1410'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function list(spec, keys, fallback = []) {
  for (const key of keys) {
    const value = spec.content?.[key]
    if (Array.isArray(value)) {
      const cleaned = value.filter((item) => typeof item === 'string' && item.trim()).map((item) => item.trim())
      if (cleaned.length) return cleaned
    }
  }
  return fallback
}

function splitPosterTitle(title) {
  const cleaned = title || 'Apex Group Ltd.'
  const words = cleaned.split(/\s+/).filter(Boolean)
  if (words.length >= 3) {
    return {
      top: words[0],
      red: words[1],
      tail: words.slice(2).join(' ')
    }
  }
  if (words.length === 2) {
    return { top: words[0], red: words[1], tail: 'Ltd.' }
  }
  return { top: cleaned, red: 'Group', tail: 'Ltd.' }
}

function offsetTitle(value, style, theme, spec) {
  return [
    Title(value, {
      ...style,
      left: style.left + 5,
      top: style.top + 5,
      color: theme.text,
      opacity: 0.16,
      ...fontRole('display', spec, { fontWeight: 900 })
    }),
    Title(value, {
      ...style,
      left: style.left + 2,
      top: style.top + 2,
      color: theme.text,
      opacity: 0.22,
      ...fontRole('display', spec, { fontWeight: 900 })
    }),
    Title(value, {
      ...style,
      color: theme.red,
      ...fontRole('display', spec, { fontWeight: 900 })
    })
  ]
}

export function renderPosterStatPunch(spec) {
  const theme = colors(spec)
  const parts = splitPosterTitle(text(spec, 'title', 'Apex Group Ltd.'))
  const pillars = list(spec, ['pillars', 'items'], ['Regional momentum', 'Portfolio expansion', 'Operating discipline']).slice(0, 3)
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.background,
      color: theme.text,
      overflow: 'hidden'
    },
    [
      TextBlock(text(spec, 'eyebrow', 'Q2 Strategy Overview').toUpperCase(), {
        position: 'absolute',
        left: 68,
        top: 58,
        width: 240,
        color: theme.muted,
        fontSize: 7,
        lineHeight: 1,
        ...fontRole('label', spec, { fontWeight: 800 })
      }),
      Title(parts.top, {
        position: 'absolute',
        left: 66,
        top: 86,
        width: 372,
        color: theme.text,
        fontSize: 48,
        lineHeight: 0.92,
        transform: 'rotate(-4deg)',
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      ...offsetTitle(parts.red, {
        position: 'absolute',
        left: 65,
        top: 131,
        width: 420,
        fontSize: 58,
        lineHeight: 0.86,
        transform: 'rotate(-4deg)'
      }, theme, spec),
      Title(parts.tail, {
        position: 'absolute',
        left: 292,
        top: 146,
        width: 274,
        color: theme.text,
        fontSize: 38,
        lineHeight: 0.9,
        transform: 'rotate(2deg)',
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, 'subtitle', 'A confident poster-scale claim for a decision-ready deck.'), {
        position: 'absolute',
        right: 76,
        bottom: 82,
        width: 278,
        color: theme.text,
        fontSize: 11,
        lineHeight: 1.55,
        textAlign: 'right',
        ...fontRole('body', spec)
      }),
      TextBlock(text(spec, 'date', '2026'), {
        position: 'absolute',
        right: 76,
        bottom: 54,
        width: 120,
        color: theme.muted,
        fontSize: 8,
        textAlign: 'right',
        ...fontRole('label', spec, { fontWeight: 800 })
      }),
      box({ position: 'absolute', left: 66, bottom: 64, width: 86, height: 2, backgroundColor: theme.red }),
      box({ position: 'absolute', left: 66, bottom: 44, width: 704, height: 2, backgroundColor: theme.red }),
      box(
        {
          position: 'absolute',
          left: 382,
          top: 272,
          width: 404,
          flexDirection: 'row',
          borderTopWidth: 2,
          borderTopColor: theme.line,
          borderBottomWidth: 2,
          borderBottomColor: theme.line
        },
        pillars.map((pillar, index) =>
          box(
            {
              width: 134,
              minHeight: 94,
              flexDirection: 'column',
              borderLeftWidth: index === 0 ? 0 : 1,
              borderLeftColor: theme.line,
              padding: '13px 14px'
            },
            [
              TextBlock(String(index + 1).padStart(2, '0'), {
                color: theme.red,
                fontSize: 17,
                lineHeight: 1,
                marginBottom: 8,
                ...fontRole('metric', spec, { fontWeight: 900 })
              }),
              TextBlock(pillar, {
                color: theme.text,
                fontSize: 10,
                lineHeight: 1.35,
                ...fontRole('body', spec)
              })
            ]
          )
        )
      ),
      TextBlock(text(spec, 'stat', ''), {
        position: 'absolute',
        right: 78,
        top: 58,
        width: 160,
        color: theme.red,
        fontSize: 18,
        textAlign: 'right',
        ...fontRole('metric', spec, { fontWeight: 900 })
      })
    ]
  )
}
