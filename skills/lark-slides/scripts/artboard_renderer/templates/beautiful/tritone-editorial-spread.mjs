import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'tritone-editorial-spread'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'editorial-tri-tone',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/editorial-tri-tone-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    pink: source.background || '#F2B6C6',
    yellow: source.accent || '#F2D86A',
    burgundy: source.primary || '#7A1F35',
    text: source.text || '#7A1F35'
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

function pill(theme, spec, label, index) {
  const dark = index % 2 === 0
  return TextBlock(label.toLowerCase(), {
    height: 38,
    minWidth: Math.max(92, label.length * 17),
    padding: '4px 18px',
    borderRadius: 20,
    color: dark ? theme.yellow : theme.burgundy,
    backgroundColor: dark ? theme.burgundy : theme.yellow,
    ...fontRole('body', spec, { fontWeight: 900 }),
    fontSize: 21,
    lineHeight: 1.35
  })
}

function titleParts(title) {
  const cleaned = title || 'Studio & Salon'
  if (cleaned.includes('&')) {
    const [left, right] = cleaned.split('&')
    return { left: left.trim() || 'Studio', right: right.trim() || 'Salon' }
  }
  const words = cleaned.split(/\s+/).filter(Boolean)
  const half = Math.max(1, Math.ceil(words.length / 2))
  return {
    left: words.slice(0, half).join(' ') || 'Studio',
    right: words.slice(half).join(' ') || 'Salon'
  }
}

export function renderTritoneEditorialSpread(spec) {
  const theme = colors(spec)
  const labels = list(spec, ['points', 'tags'], [
    'focus',
    'tech-equipped',
    'creativity',
    'coffee',
    'community',
    'coworking',
    'productivity',
    'inspiration',
    'flexible',
    'workshops',
    'collaboration',
    'studio'
  ]).slice(0, 12)
  const parts = titleParts(text(spec, 'title', 'Studio & Salon'))
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.pink,
      color: theme.text,
      overflow: 'hidden'
    },
    [
      TextBlock(text(spec, 'left_meta', 'VOL. 04 — EDITORIAL BRIEF').toUpperCase(), {
        position: 'absolute',
        left: 32,
        top: 34,
        color: theme.burgundy,
        ...fontRole('label', spec, { fontWeight: 800 }),
        fontSize: 13,
        letterSpacing: 5
      }),
      TextBlock(text(spec, 'center_meta', 'SPRING / SUMMER EDITION').toUpperCase(), {
        position: 'absolute',
        left: 344,
        top: 34,
        width: 280,
        color: theme.burgundy,
        textAlign: 'center',
        ...fontRole('label', spec, { fontWeight: 800 }),
        fontSize: 13,
        letterSpacing: 5,
      }),
      TextBlock(text(spec, 'right_meta', 'FW · 2026').toUpperCase(), {
        position: 'absolute',
        right: 32,
        top: 34,
        width: 130,
        color: theme.burgundy,
        textAlign: 'right',
        ...fontRole('metric', spec, { fontWeight: 800 }),
        fontSize: 13,
        letterSpacing: 5,
      }),
      box(
        {
          position: 'absolute',
          left: 32,
          top: 60,
          width: 760,
          flexDirection: 'row',
          flexWrap: 'wrap',
          gap: 11
        },
        labels.map((label, index) => pill(theme, spec, label, index))
      ),
      Title(parts.left, {
        position: 'absolute',
        left: 32,
        bottom: 45,
        width: 420,
        color: theme.burgundy,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 98,
        lineHeight: 0.9
      }),
      Title('&', {
        position: 'absolute',
        left: 446,
        bottom: 47,
        width: 86,
        color: theme.yellow,
        textAlign: 'center',
        ...fontRole('display', spec, { fontWeight: 500 }),
        fontSize: 105,
        lineHeight: 0.85
      }),
      Title(parts.right, {
        position: 'absolute',
        right: 28,
        bottom: 45,
        width: 410,
        color: theme.burgundy,
        textAlign: 'right',
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 98,
        lineHeight: 0.9
      })
    ]
  )
}
