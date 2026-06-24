import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'executive-dashboard'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'production',
  renderer_stage: 'closed_loop_sample',
  default_selectable: true,
  selection_scope: 'production',
  source_family: 'blue-professional',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/blue-professional-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    background: source.background || '#FDFAE7',
    panel: source.panel || '#FFFFFF',
    surface: source.surface || '#F5F7FF',
    primary: source.primary || '#1E2BFA',
    accent: source.accent || '#1E2BFA',
    text: source.text || '#111111',
    muted: source.muted || '#6B6B6B',
    border: source.border || '#D4D8FE'
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

export function renderExecutiveDashboard(spec) {
  const theme = colors(spec)
  const footer = text(spec, 'footer', 'Q2 2026 · Confidential')
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
      box({
        position: 'absolute',
        right: -86,
        top: -56,
        width: 374,
        height: 660,
        backgroundColor: '#E8E7E6',
        transform: 'skewX(-10deg)'
      }),
      box({ position: 'absolute', left: 0, bottom: 0, width: 96, height: 2, backgroundColor: theme.primary }),
      box({ position: 'absolute', left: 77, top: 183, width: 30, height: 2, backgroundColor: theme.primary }),
      TextBlock(text(spec, 'eyebrow', 'EXECUTIVE REVIEW').toUpperCase(), {
        position: 'absolute',
        left: 78,
        top: 178,
        color: theme.primary,
        fontSize: 1,
        letterSpacing: 0,
        ...fontRole('label', spec, { fontWeight: 900 })
      }),
      Title(text(spec, 'title', '内部业务复盘'), {
        position: 'absolute',
        left: 77,
        top: 199,
        width: 420,
        color: theme.text,
        fontSize: 38,
        lineHeight: 1.08,
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, 'subtitle', '指标、证据与行动计划'), {
        position: 'absolute',
        left: 78,
        top: 282,
        width: 440,
        color: theme.muted,
        fontSize: 12,
        lineHeight: 1.35,
        ...fontRole('body', spec)
      }),
      TextBlock(footer, {
        position: 'absolute',
        left: 77,
        top: 337,
        width: 220,
        color: theme.muted,
        fontSize: 7,
        lineHeight: 1,
        ...fontRole('label', spec)
      }),
      box({ position: 'absolute', right: 77, bottom: 63, width: 30, height: 30, flexDirection: 'row', flexWrap: 'wrap', gap: 5 },
        Array.from({ length: 9 }).map((_, index) =>
          box({ width: 3, height: 3, backgroundColor: theme.primary, opacity: 0.28 })
        )
      ),
      TextBlock('1 / 10', {
        position: 'absolute',
        left: 28,
        bottom: 14,
        width: 48,
        color: theme.muted,
        fontSize: 7,
        ...fontRole('metric', spec)
      })
    ]
  )
}
