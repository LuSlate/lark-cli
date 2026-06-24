import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'block-frame-grid'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'block-frame',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/block-frame-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    background: source.background || '#FFDC8B',
    paper: source.surface || '#FFFDF5',
    black: source.text || '#000000',
    pink: source.primary || '#FE90E8',
    green: source.accent || '#99E885',
    yellow: source.yellow || '#F7CB46',
    blue: source.blue || '#C0F7FE',
    white: '#FFFFFF'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function dotGrid(theme) {
  return Array.from({ length: 24 }).map((_, index) =>
    box({
      position: 'absolute',
      left: 34 + (index % 6) * 10,
      top: 35 + Math.floor(index / 6) * 10,
      width: 2,
      height: 2,
      borderRadius: 1,
      backgroundColor: theme.black,
      opacity: 0.55
    })
  )
}

function framedButton(theme, spec, label, style = {}) {
  return box(
    {
      width: 54,
      height: 24,
      backgroundColor: theme.white,
      borderWidth: 2,
      borderColor: theme.black,
      alignItems: 'center',
      justifyContent: 'center',
      ...style
    },
    [
      TextBlock(label, {
        color: theme.black,
        fontSize: 12,
        lineHeight: 1,
        textAlign: 'center',
        ...fontRole('metric', spec, { fontWeight: 900 })
      })
    ]
  )
}

function shadowCard(theme, children) {
  return [
    box({ position: 'absolute', left: 264, top: 147, width: 452, height: 274, backgroundColor: theme.black }),
    box(
      {
        position: 'absolute',
        left: 256,
        top: 139,
        width: 452,
        height: 274,
        flexDirection: 'column',
        backgroundColor: theme.paper,
        borderWidth: 3,
        borderColor: theme.black,
        padding: '30px 32px'
      },
      children
    )
  ]
}

export function renderBlockFrameGrid(spec) {
  const theme = colors(spec)
  const title = text(spec, 'title', 'NEO-BRUTALISM STYLE').toUpperCase()
  const subtitle = text(spec, 'subtitle', 'A bold, high-contrast template designed for maximum visual impact and uncompromising clarity.')
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.background,
      color: theme.black,
      overflow: 'hidden'
    },
    [
      ...dotGrid(theme),
      ...shadowCard(theme, [
        TextBlock(text(spec, 'eyebrow', 'PRESENTATION TEMPLATE').toUpperCase(), {
          width: 110,
          height: 20,
          borderWidth: 2,
          borderColor: theme.black,
          color: theme.black,
          fontSize: 8,
          lineHeight: 1,
          padding: '5px 7px',
          marginBottom: 16,
          ...fontRole('label', spec, { fontWeight: 900 })
        }),
        Title(title, {
          width: 330,
          color: theme.black,
          fontSize: 51,
          lineHeight: 0.92,
          marginBottom: 16,
          ...fontRole('display', spec, { fontWeight: 900 })
        }),
        TextBlock(subtitle, {
          width: 318,
          color: theme.black,
          fontSize: 11,
          lineHeight: 1.35,
          ...fontRole('body', spec, { fontWeight: 700 })
        })
      ]),
      box({ position: 'absolute', left: 614, top: 118, width: 58, height: 52, backgroundColor: theme.black, transform: 'rotate(12deg)' }),
      box({
        position: 'absolute',
        left: 610,
        top: 112,
        width: 58,
        height: 52,
        backgroundColor: theme.pink,
        borderWidth: 2,
        borderColor: theme.black,
        transform: 'rotate(12deg)'
      }),
      box({ position: 'absolute', left: 616, top: 348, width: 32, height: 32, borderRadius: 16, backgroundColor: theme.green, borderWidth: 2, borderColor: theme.black }),
      box({ position: 'absolute', left: 298, top: 401, width: 72, height: 20, backgroundColor: theme.black, transform: 'rotate(-2deg)' }),
      box(
        {
          position: 'absolute',
          left: 296,
          top: 397,
          width: 72,
          height: 20,
          backgroundColor: theme.yellow,
          borderWidth: 2,
          borderColor: theme.black,
          alignItems: 'center',
          justifyContent: 'center',
          transform: 'rotate(-2deg)'
        },
        [
          TextBlock(text(spec, 'cta', 'Get Started'), {
            color: theme.black,
            fontSize: 7,
            lineHeight: 1,
            ...fontRole('label', spec, { fontWeight: 900 })
          })
        ]
      ),
      framedButton(theme, spec, text(spec, 'page', '01 / 10'), { position: 'absolute', left: 12, bottom: 10, width: 48 }),
      box(
        { position: 'absolute', right: 12, bottom: 10, flexDirection: 'row', gap: 8 },
        [
          framedButton(theme, spec, '<', { width: 24 }),
          framedButton(theme, spec, '>', { width: 24 })
        ]
      ),
      box({ position: 'absolute', left: 462, top: 136, width: 10, height: 10, backgroundColor: theme.blue, borderWidth: 2, borderColor: theme.black })
    ]
  )
}
