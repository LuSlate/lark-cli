import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'daisy-workshop-playbook'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'daisy-days',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/daisy-days-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    cream: source.background || '#F5F0E6',
    ink: source.text || '#2D2D2D',
    muted: source.muted || '#696765',
    yellow: source.panel || '#FDE68A',
    pink: source.primary || '#F7C8D4',
    mint: source.accent || '#7ECDC0',
    white: source.surface || '#FFFFFF'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function petal(theme, left, top, rotation) {
  return box({
    position: 'absolute',
    left,
    top,
    width: 44,
    height: 76,
    borderRadius: 24,
    borderWidth: 2,
    borderColor: theme.ink,
    backgroundColor: theme.white,
    transform: `rotate(${rotation}deg)`
  })
}

function flower(theme, left, top, scale = 1) {
  const size = 112 * scale
  const petalWidth = 44 * scale
  const petalHeight = 76 * scale
  return box(
    { position: 'absolute', left, top, width: size, height: size },
    [
      ...[0, 45, 90, 135, 180, 225, 270, 315].map((rotation, index) =>
        box({
          position: 'absolute',
          left: 34 * scale + Math.cos((rotation * Math.PI) / 180) * 26 * scale,
          top: 18 * scale + Math.sin((rotation * Math.PI) / 180) * 26 * scale,
          width: petalWidth,
          height: petalHeight,
          borderRadius: 24 * scale,
          borderWidth: 2,
          borderColor: theme.ink,
          backgroundColor: theme.white,
          transform: `rotate(${rotation}deg)`,
          opacity: index % 2 === 0 ? 1 : 0.96
        })
      ),
      box({
        position: 'absolute',
        left: 42 * scale,
        top: 42 * scale,
        width: 34 * scale,
        height: 34 * scale,
        borderRadius: 17 * scale,
        borderWidth: 2,
        borderColor: theme.ink,
        backgroundColor: theme.yellow
      })
    ]
  )
}

function star(theme, left, top, color) {
  return box({
    position: 'absolute',
    left,
    top,
    width: 36,
    height: 36,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: theme.ink,
    backgroundColor: color,
    transform: 'rotate(35deg)'
  })
}

function dotRail(theme) {
  return Array.from({ length: 10 }).map((_, index) =>
    box({
      position: 'absolute',
      right: 12,
      top: 218 + index * 11,
      width: 6,
      height: 6,
      borderRadius: 3,
      borderWidth: 1.5,
      borderColor: theme.ink,
      backgroundColor: index === 0 ? theme.yellow : 'transparent'
    })
  )
}

export function renderDaisyWorkshopPlaybook(spec) {
  const theme = colors(spec)
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
      flower(theme, -24, -10, 0.82),
      flower(theme, 878, 14, 0.56),
      flower(theme, 22, 462, 0.7),
      flower(theme, 874, 432, 0.82),
      star(theme, 68, 72, theme.pink),
      star(theme, 846, 100, theme.mint),
      star(theme, 104, 408, theme.yellow),
      ...dotRail(theme),
      TextBlock(text(spec, 'eyebrow', 'Workshop Playbook').toUpperCase(), {
        position: 'absolute',
        left: 340,
        top: 198,
        width: 280,
        color: theme.ink,
        textAlign: 'center',
        ...fontRole('label', spec, { fontWeight: 900 }),
        fontSize: 11,
        lineHeight: 1
      }),
      Title(text(spec, 'title', 'Daisy Days'), {
        position: 'absolute',
        left: 200,
        top: 230,
        width: 520,
        color: theme.ink,
        textAlign: 'center',
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 76,
        lineHeight: 1
      }),
      TextBlock(text(spec, 'subtitle', 'A cheerful presentation template for bright moments'), {
        position: 'absolute',
        left: 220,
        top: 314,
        width: 520,
        color: theme.ink,
        textAlign: 'center',
        ...fontRole('body', spec, { fontWeight: 900 }),
        fontSize: 20,
        lineHeight: 1.25
      }),
      box({
        position: 'absolute',
        left: 420,
        top: 354,
        width: 120,
        height: 2,
        borderRadius: 1,
        backgroundColor: theme.ink
      }),
      box(
        {
          position: 'absolute',
          left: 390,
          bottom: 8,
          width: 180,
          height: 28,
          borderRadius: 10,
          backgroundColor: theme.ink
        }
      ),
      box(
        {
          position: 'absolute',
          left: 410,
          bottom: 18,
          width: 140,
          height: 18,
          borderRadius: 10,
          borderWidth: 2,
          borderColor: theme.ink,
          backgroundColor: theme.white,
          alignItems: 'center',
          justifyContent: 'center'
        },
        [
          TextBlock(text(spec, 'page', '1 / 10'), {
            color: theme.ink,
            ...fontRole('metric', spec, { fontWeight: 900 }),
            fontSize: 8,
            lineHeight: 1
          })
        ]
      )
    ]
  )
}
