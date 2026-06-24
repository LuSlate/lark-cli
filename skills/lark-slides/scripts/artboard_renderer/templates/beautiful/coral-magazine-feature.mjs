import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'coral-magazine-feature'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'coral',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/coral-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    coral: source.primary || '#E85D5D',
    coralDark: source.accent || '#C45252',
    cream: source.background || '#F5F0E8',
    creamDark: source.panel || '#E8E0D4',
    ink: source.text || '#1A1A1A',
    gray: source.muted || '#6B6B6B',
    white: '#FFFFFF'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function coralChevrons(theme) {
  const shapes = []
  for (let index = -1; index < 7; index += 1) {
    const left = index * 160 + 40
    shapes.push(box({
      position: 'absolute',
      left,
      top: 10,
      width: 28,
      height: 210,
      backgroundColor: theme.coralDark,
      opacity: 0.62,
      transform: 'rotate(26deg)'
    }))
    shapes.push(box({
      position: 'absolute',
      left: left + 70,
      top: 10,
      width: 28,
      height: 210,
      backgroundColor: theme.coralDark,
      opacity: 0.62,
      transform: 'rotate(-26deg)'
    }))
    shapes.push(box({
      position: 'absolute',
      left: left + 26,
      top: 58,
      width: 14,
      height: 142,
      backgroundColor: theme.coralDark,
      opacity: 0.42,
      transform: 'rotate(26deg)'
    }))
    shapes.push(box({
      position: 'absolute',
      left: left + 79,
      top: 58,
      width: 14,
      height: 142,
      backgroundColor: theme.coralDark,
      opacity: 0.42,
      transform: 'rotate(-26deg)'
    }))
  }
  return shapes
}

export function renderCoralMagazineFeature(spec) {
  const theme = colors(spec)
  const title = text(spec, 'title', 'Quarterly Strategy Session 2026')
  const titleLines = title.toUpperCase().split(/\s+/)
  const first = titleLines.slice(0, 1).join(' ')
  const second = titleLines.slice(1, 2).join(' ')
  const third = titleLines.slice(2).join(' ')
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.cream,
      color: theme.ink,
      overflow: 'hidden'
    },
    [
      box({ position: 'absolute', left: 0, top: 0, width: 960, height: 172, backgroundColor: theme.coral },
        coralChevrons(theme)
      ),
      TextBlock(text(spec, 'eyebrow', 'VENTURE').toUpperCase(), {
        position: 'absolute',
        left: 50,
        top: 23,
        color: theme.ink,
        ...fontRole('label', spec, { fontWeight: 900 }),
        fontSize: 7,
        letterSpacing: 4
      }),
      Title(first || 'QUARTERLY', {
        position: 'absolute',
        left: 50,
        top: 197,
        width: 500,
        color: theme.ink,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 43,
        lineHeight: 0.9
      }),
      Title(second || 'STRATEGY', {
        position: 'absolute',
        left: 50,
        top: 250,
        width: 520,
        color: theme.ink,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 43,
        lineHeight: 0.9
      }),
      Title(third || 'SESSION 2026', {
        position: 'absolute',
        left: 50,
        top: 305,
        width: 620,
        color: theme.ink,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 43,
        lineHeight: 0.9
      }),
      box({ position: 'absolute', left: 50, top: 372, width: 860, height: 1, backgroundColor: theme.creamDark }),
      ...Array.from({ length: 10 }).map((_, index) =>
        box({
          position: 'absolute',
          right: 30,
          top: 218 + index * 11,
          width: 5,
          height: 5,
          borderRadius: 3,
          backgroundColor: index === 0 ? theme.coral : theme.white,
          opacity: index === 0 ? 1 : 0.78
        })
      ),
      TextBlock(text(spec, 'location_label', 'LOCATION').toUpperCase(), {
        position: 'absolute',
        left: 50,
        bottom: 43,
        color: theme.gray,
        ...fontRole('label', spec, { fontWeight: 800 }),
        fontSize: 7,
        letterSpacing: 3
      }),
      TextBlock(text(spec, 'location', '7TH FLOOR').toUpperCase(), {
        position: 'absolute',
        left: 50,
        bottom: 24,
        color: theme.ink,
        ...fontRole('body', spec, { fontWeight: 900 }),
        fontSize: 19,
        lineHeight: 1
      }),
      TextBlock(text(spec, 'date', 'MAY 15 / 09:00 START').toUpperCase(), {
        position: 'absolute',
        right: 50,
        bottom: 44,
        width: 210,
        color: theme.gray,
        textAlign: 'right',
        ...fontRole('label', spec, { fontWeight: 800 }),
        fontSize: 7,
        letterSpacing: 2,
      }),
      TextBlock(text(spec, 'year', '2026'), {
        position: 'absolute',
        right: 50,
        bottom: 24,
        width: 70,
        color: theme.ink,
        textAlign: 'right',
        ...fontRole('metric', spec, { fontWeight: 900 }),
        fontSize: 20,
        lineHeight: 1
      }),
      TextBlock('01 / 10', {
        position: 'absolute',
        right: 20,
        bottom: 11,
        color: theme.white,
        ...fontRole('metric', spec),
        fontSize: 7
      })
    ]
  )
}
