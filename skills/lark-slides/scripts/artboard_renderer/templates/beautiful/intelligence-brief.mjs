import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'intelligence-brief'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'signal',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/signal-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    background: source.background || '#1C2644',
    backgroundAlt: source.surface || '#232F55',
    text: source.text || '#E2DCD0',
    muted: source.muted || '#8A96A8',
    hint: source.hint || '#4E5A6E',
    accent: source.accent || '#C8A870',
    border: source.border || '#2E3D5C'
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

function gridTexture(theme) {
  const lines = []
  for (let x = 80; x < 960; x += 80) {
    lines.push(box({ position: 'absolute', left: x, top: 0, width: 1, height: 540, backgroundColor: theme.hint, opacity: 0.72 }))
  }
  for (let y = 80; y < 540; y += 80) {
    lines.push(box({ position: 'absolute', left: 0, top: y, width: 960, height: 1, backgroundColor: theme.hint, opacity: 0.72 }))
  }
  lines.push(box({ position: 'absolute', left: 64, top: 64, width: 832, height: 1, backgroundColor: theme.border, opacity: 0.74 }))
  lines.push(box({ position: 'absolute', left: 64, bottom: 50, width: 832, height: 1, backgroundColor: theme.border, opacity: 0.7 }))
  return lines
}

function bracketedTitle(title) {
  const cleaned = title || 'Presentation Title'
  if (cleaned.includes('[')) return cleaned
  const parts = cleaned.split(/\s+/)
  if (parts.length <= 1) return `[${cleaned}]`
  return `[${parts.slice(0, -1).join(' ')}]\n${parts[parts.length - 1]}`
}

function metadataRow(spec, theme) {
  const left = text(spec, 'eyebrow', 'PRIVATE INTELLIGENCE NOTE').toUpperCase()
  const right = text(spec, 'date', 'JUNE 2026').toUpperCase()
  return [
    TextBlock(left, {
      position: 'absolute',
      left: 64,
      top: 48,
      color: theme.muted,
      fontSize: 7,
      lineHeight: 1,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    TextBlock(right, {
      position: 'absolute',
      right: 64,
      top: 48,
      width: 160,
      color: theme.muted,
      fontSize: 7,
      lineHeight: 1,
      textAlign: 'right',
      ...fontRole('label', spec, { fontWeight: 700 })
    })
  ]
}

export function renderIntelligenceBrief(spec) {
  const theme = colors(spec)
  const points = list(spec, ['points', 'items'], ['Current limitation or source of friction', 'Expected improvement or capability', 'Decision owner and next signal']).slice(0, 3)
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
      ...gridTexture(theme),
      ...metadataRow(spec, theme),
      box({ position: 'absolute', left: 64, top: 127, width: 34, height: 1, backgroundColor: theme.accent }),
      Title(bracketedTitle(text(spec, 'title', 'Presentation Title')), {
        position: 'absolute',
        left: 64,
        top: 147,
        width: 445,
        color: theme.text,
        fontSize: 47,
        lineHeight: 0.94,
        whiteSpace: 'pre-wrap',
        ...fontRole('display', spec, { fontWeight: 800 })
      }),
      TextBlock(text(spec, 'subtitle', 'A short description of the deck, its purpose, and the decision it supports.'), {
        position: 'absolute',
        left: 66,
        top: 284,
        width: 360,
        color: theme.muted,
        fontSize: 10,
        lineHeight: 1.55,
        ...fontRole('body', spec)
      }),
      box({
        position: 'absolute',
        left: 64,
        top: 344,
        width: 112,
        height: 1,
        backgroundColor: theme.accent,
        opacity: 0.88
      }),
      box(
        {
          position: 'absolute',
          right: 68,
          top: 156,
          width: 250,
          flexDirection: 'column'
        },
        points.map((point, index) =>
          box(
            {
              minHeight: 52,
              flexDirection: 'row',
              borderTopWidth: 1,
              borderTopColor: index === 0 ? theme.accent : theme.border,
              padding: '13px 0'
            },
            [
              TextBlock(String(index + 1).padStart(2, '0'), {
                width: 42,
                color: theme.accent,
                fontSize: 12,
                lineHeight: 1,
                ...fontRole('metric', spec, { fontWeight: 800 })
              }),
              TextBlock(point, {
                flex: 1,
                color: theme.muted,
                fontSize: 9,
                lineHeight: 1.45,
                ...fontRole('body', spec)
              })
            ]
          )
        )
      ),
      TextBlock(text(spec, 'footer_left', 'PRIVATE / RESEARCH'), {
        position: 'absolute',
        left: 64,
        bottom: 33,
        width: 190,
        color: theme.hint,
        fontSize: 7,
        ...fontRole('label', spec, { fontWeight: 700 })
      }),
      TextBlock(text(spec, 'footer_right', 'CONFIDENTIAL'), {
        position: 'absolute',
        right: 64,
        bottom: 33,
        width: 160,
        color: theme.hint,
        fontSize: 7,
        textAlign: 'right',
        ...fontRole('label', spec, { fontWeight: 700 })
      })
    ]
  )
}
