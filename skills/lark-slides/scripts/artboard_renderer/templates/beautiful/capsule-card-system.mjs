import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'capsule-card-system'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'capsule',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/capsule-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    background: source.background || '#F4F4EE',
    ink: source.text || '#1A1A1A',
    muted: source.muted || '#77736D',
    yellow: source.panel || '#F2D160',
    coral: source.accent || '#E85D4E',
    lavender: source.lavender || '#CDB9E9',
    blue: source.blue || '#8DB7F2',
    lime: source.primary || '#C4D94E',
    peach: source.peach || '#F0B894'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function pill(theme, spec, value, style = {}) {
  return box(
    {
      position: 'absolute',
      minWidth: 84,
      height: 34,
      padding: '8px 18px',
      borderRadius: 999,
      borderWidth: 2,
      borderColor: theme.ink,
      backgroundColor: theme.yellow,
      alignItems: 'center',
      justifyContent: 'center',
      ...style
    },
    [
      TextBlock(value, {
        color: theme.ink,
        fontSize: 11,
        lineHeight: 1,
        textAlign: 'center',
        ...fontRole('label', spec, { fontWeight: 900 })
      })
    ]
  )
}

function dotRail(theme) {
  return Array.from({ length: 10 }).map((_, index) =>
    box({
      position: 'absolute',
      right: 34,
      top: 220 + index * 11,
      width: 6,
      height: 6,
      borderRadius: 3,
      borderWidth: index === 0 ? 0 : 1.5,
      borderColor: theme.ink,
      backgroundColor: index === 0 ? theme.ink : 'transparent'
    })
  )
}

export function renderCapsuleCardSystem(spec) {
  const theme = colors(spec)
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.background,
      color: theme.ink,
      overflow: 'hidden'
    },
    [
      box({ position: 'absolute', left: 0, top: 0, width: 330, height: 540, backgroundColor: '#EEEEEA' }),
      box({ position: 'absolute', right: 0, top: 0, width: 260, height: 540, backgroundColor: '#EEF2DE' }),
      box({ position: 'absolute', left: 190, bottom: 0, width: 420, height: 190, backgroundColor: '#EFEFDF' }),
      pill(theme, spec, text(spec, 'capsules', 'Concept').split(',')[0] || 'Concept', { left: 78, top: 67, backgroundColor: theme.coral, transform: 'rotate(-12deg)' }),
      pill(theme, spec, text(spec, 'stat', '2026'), { left: 432, top: 82, width: 44, height: 44, borderRadius: 22, backgroundColor: theme.peach, padding: '14px 0', transform: 'rotate(0deg)' }),
      pill(theme, spec, 'Strategy', { right: 86, top: 100, backgroundColor: theme.lavender, transform: 'rotate(8deg)' }),
      pill(theme, spec, 'Vision', { left: 144, bottom: 128, backgroundColor: theme.blue, transform: 'rotate(7deg)' }),
      pill(theme, spec, 'Next', { left: 48, bottom: 90, width: 44, height: 44, borderRadius: 22, backgroundColor: '#9E67E8', padding: '16px 0' }),
      pill(theme, spec, 'Future', { right: 174, bottom: 80, backgroundColor: theme.lime, transform: 'rotate(-9deg)' }),
      pill(theme, spec, 'Design', { right: 78, bottom: 152, backgroundColor: 'transparent', borderColor: theme.muted, color: theme.muted, transform: 'rotate(14deg)' }),
      ...dotRail(theme),
      pill(theme, spec, text(spec, 'eyebrow', 'Presentation Template'), {
        left: 402,
        top: 210,
        width: 156,
        height: 34,
        backgroundColor: theme.yellow,
        transform: 'rotate(0deg)'
      }),
      Title(text(spec, 'title', 'CAPSULE').toUpperCase(), {
        position: 'absolute',
        left: 230,
        top: 264,
        width: 500,
        color: theme.ink,
        fontSize: 66,
        lineHeight: 1,
        textAlign: 'center',
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, 'subtitle', 'A framework for bold ideas').toUpperCase(), {
        position: 'absolute',
        left: 280,
        top: 330,
        width: 400,
        color: theme.muted,
        fontSize: 12,
        letterSpacing: 3,
        textAlign: 'center',
        ...fontRole('body', spec, { fontWeight: 700 })
      }),
      TextBlock('USE ARROW KEYS TO NAVIGATE', {
        position: 'absolute',
        left: 16,
        bottom: 16,
        color: '#B6B1AA',
        fontSize: 7,
        ...fontRole('label', spec, { fontWeight: 700 })
      }),
      TextBlock(text(spec, 'page', '01 / 10'), {
        position: 'absolute',
        right: 16,
        bottom: 16,
        color: theme.muted,
        fontSize: 8,
        ...fontRole('metric', spec, { fontWeight: 700 })
      })
    ]
  )
}
