import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'type-mass-poster'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'studio',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/studio-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    black: source.background || '#1C1C1C',
    yellow: source.primary || '#F5D200',
    muted: source.muted || '#9A860C'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

export function renderTypeMassPoster(spec) {
  const theme = colors(spec)
  const title = text(spec, 'title', 'PROPOSAL').toUpperCase()
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.black,
      color: theme.yellow,
      overflow: 'hidden'
    },
    [
      Title(title, {
        position: 'absolute',
        left: 52,
        top: 42,
        width: 720,
        color: theme.yellow,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: title.length <= 9 ? 112 : 86,
        lineHeight: 0.88
      }),
      TextBlock(text(spec, 'image_label', 'IMAGE PLACEHOLDER').toUpperCase(), {
        position: 'absolute',
        left: 438,
        top: 267,
        width: 210,
        color: theme.muted,
        ...fontRole('label', spec, { fontWeight: 800 }),
        fontSize: 9,
        lineHeight: 1
      }),
      box({ position: 'absolute', left: 0, bottom: 64, width: 960, height: 1, backgroundColor: theme.yellow, opacity: 0.45 }),
      TextBlock(text(spec, 'footer_left', '[Studio Name] × [Client Name]\n[Date]'), {
        position: 'absolute',
        left: 50,
        bottom: 26,
        width: 260,
        color: theme.yellow,
        ...fontRole('metric', spec, { fontWeight: 800 }),
        fontSize: 10,
        lineHeight: 1.55,
        whiteSpace: 'pre-wrap'
      }),
      TextBlock(text(spec, 'footer_center', '[Presentation Title]'), {
        position: 'absolute',
        left: 382,
        bottom: 42,
        width: 210,
        color: theme.yellow,
        textAlign: 'center',
        ...fontRole('body', spec, { fontWeight: 800 }),
        fontSize: 10,
        lineHeight: 1
      }),
      TextBlock(text(spec, 'footer_right', '[Studio Name]'), {
        position: 'absolute',
        right: 50,
        bottom: 42,
        width: 190,
        color: theme.yellow,
        textAlign: 'right',
        ...fontRole('metric', spec, { fontWeight: 800 }),
        fontSize: 10,
        lineHeight: 1
      }),
      TextBlock(text(spec, 'page', '1 / 12'), {
        position: 'absolute',
        right: 22,
        bottom: 10,
        width: 60,
        color: theme.muted,
        textAlign: 'right',
        ...fontRole('metric', spec, { fontWeight: 800 }),
        fontSize: 7
      })
    ]
  )
}
