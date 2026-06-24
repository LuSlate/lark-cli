import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'soft-editorial-feature'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'soft-editorial',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/soft-editorial-4.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    paper: source.background || '#F2EEDF',
    ink: source.text || '#2A241B',
    inkSoft: source.muted || '#5C5345',
    pink: source.pink || '#E1A4C2',
    lemon: source.lemon || '#D6DD63',
    blush: source.blush || '#E8C9B6',
    sage: source.sage || '#B7C7A8'
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

function card(theme, spec, { left, color, index, title, subtitle }) {
  return box(
    {
      position: 'absolute',
      left,
      top: 100,
      width: 284,
      height: 340,
      flexDirection: 'column',
      alignItems: 'center',
      backgroundColor: color,
      borderRadius: 18,
      padding: '36px 40px'
    },
    [
      Title(`Insight #${index}`, {
        color: theme.ink,
        fontSize: 33,
        lineHeight: 1,
        textAlign: 'center',
        marginBottom: 15,
        ...fontRole('display', spec, { fontWeight: 600 })
      }),
      TextBlock(title, {
        color: theme.ink,
        fontSize: 15,
        lineHeight: 1.2,
        textAlign: 'center',
        marginBottom: 24,
        ...fontRole('body', spec, { fontWeight: 800 })
      }),
      TextBlock(subtitle, {
        width: 204,
        height: 74,
        color: theme.ink,
        fontSize: 12,
        lineHeight: 1.35,
        textAlign: 'center',
        ...fontRole('body', spec, { fontWeight: 500 })
      })
    ]
  )
}

export function renderSoftEditorialFeature(spec) {
  const theme = colors(spec)
  const cards = list(spec, ['cards', 'items'], [
    'Trust is the onboarding',
    'Power users dread upgrades',
    'Support is product'
  ]).slice(0, 3)
  const descriptions = list(spec, ['descriptions', 'points'], [
    "Customers don't churn on day one because the product is hard.",
    'The people we asked to love new features quietly resent them.',
    'Feature requests often hide a discovery problem.'
  ]).slice(0, 3)
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
      TextBlock(text(spec, 'eyebrow', 'Insights'), {
        position: 'absolute',
        left: 40,
        top: 34,
        color: theme.ink,
        fontSize: 15,
        ...fontRole('label', spec, { fontWeight: 700 })
      }),
      TextBlock(text(spec, 'section_number', 'iv'), {
        position: 'absolute',
        right: 40,
        top: 36,
        color: theme.ink,
        fontSize: 12,
        ...fontRole('metric', spec, { fontWeight: 500 })
      }),
      card(theme, spec, { left: 40, color: theme.pink, index: 1, title: cards[0], subtitle: descriptions[0] }),
      card(theme, spec, { left: 338, color: theme.lemon, index: 2, title: cards[1], subtitle: descriptions[1] }),
      card(theme, spec, { left: 636, color: theme.blush, index: 3, title: cards[2], subtitle: descriptions[2] }),
      TextBlock(text(spec, 'date', 'April 29, 2026'), {
        position: 'absolute',
        left: 40,
        bottom: 31,
        color: theme.inkSoft,
        fontSize: 13,
        ...fontRole('display', spec, { fontWeight: 500 })
      }),
      TextBlock(text(spec, 'footer', 'Field Notes · Vol. III'), {
        position: 'absolute',
        right: 40,
        bottom: 31,
        width: 190,
        color: theme.inkSoft,
        fontSize: 13,
        textAlign: 'right',
        ...fontRole('display', spec, { fontWeight: 500 })
      })
    ]
  )
}
