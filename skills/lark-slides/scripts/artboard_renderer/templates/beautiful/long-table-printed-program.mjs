import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'printed-program'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'long-table',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/long-table-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    paper: source.background || '#FAF1E2',
    ink: source.primary || '#B53D2A',
    deep: source.text || '#8E2D1F',
    soft: source.panel || '#F2E5CF'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function pill(theme, spec, value, style = {}) {
  return TextBlock(value, {
    height: 22,
    minWidth: 64,
    borderWidth: 1,
    borderColor: theme.ink,
    borderRadius: 12,
    padding: '4px 15px',
    color: theme.ink,
    fontSize: 11,
    lineHeight: 1,
    textAlign: 'center',
    ...fontRole('label', spec, { fontWeight: 600 }),
    ...style
  })
}

export function renderLongTablePrintedProgram(spec) {
  const theme = colors(spec)
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
      TextBlock(text(spec, 'edition', '5'), {
        position: 'absolute',
        left: 49,
        top: 33,
        width: 22,
        height: 22,
        borderWidth: 1,
        borderColor: theme.ink,
        borderRadius: 11,
        color: theme.ink,
        fontSize: 11,
        lineHeight: 1,
        padding: '5px 0',
        textAlign: 'center',
        ...fontRole('metric', spec, { fontWeight: 500 })
      }),
      TextBlock(text(spec, 'eyebrow', 'december edition').toLowerCase(), {
        position: 'absolute',
        left: 79,
        top: 38,
        color: theme.ink,
        fontSize: 16,
        lineHeight: 1,
        ...fontRole('body', spec, { fontWeight: 800 })
      }),
      Title(text(spec, 'title', 'LONG\nTABLE').toUpperCase(), {
        position: 'absolute',
        left: 48,
        top: 126,
        width: 300,
        color: theme.ink,
        fontSize: 74,
        lineHeight: 0.88,
        whiteSpace: 'pre-line',
        ...fontRole('display', spec, { fontWeight: 900 })
      }),
      Title(text(spec, 'issue', 'No.\n05'), {
        position: 'absolute',
        right: 50,
        top: 70,
        width: 310,
        color: theme.ink,
        fontSize: 152,
        lineHeight: 0.86,
        textAlign: 'right',
        whiteSpace: 'pre-line',
        ...fontRole('display', spec, { fontWeight: 400 })
      }),
      box({ position: 'absolute', left: 48, top: 337, flexDirection: 'row', gap: 16 }, [
        pill(theme, spec, text(spec, 'city', 'Lisbon')),
        TextBlock('|', { color: theme.ink, fontSize: 16, lineHeight: 1.2, ...fontRole('body', spec) }),
        pill(theme, spec, text(spec, 'cta', 'Apply now'), { minWidth: 84 })
      ]),
      TextBlock(text(spec, 'availability', '22 seats only'), {
        position: 'absolute',
        left: 48,
        top: 374,
        color: theme.ink,
        fontSize: 12,
        lineHeight: 1.2,
        ...fontRole('body', spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, 'lede', "More than dinner, it's a long evening."), {
        position: 'absolute',
        left: 48,
        top: 394,
        width: 300,
        color: theme.ink,
        fontSize: 14,
        lineHeight: 1.35,
        ...fontRole('body', spec, { fontWeight: 600 })
      }),
      TextBlock(text(spec, 'badge', 'Not a meal, an evening'), {
        position: 'absolute',
        left: 48,
        top: 438,
        width: 160,
        height: 22,
        borderWidth: 1,
        borderColor: theme.ink,
        color: theme.ink,
        fontSize: 11,
        lineHeight: 1,
        padding: '5px 11px',
        ...fontRole('body', spec, { fontWeight: 600 })
      }),
      TextBlock(text(spec, 'right_meta', 'DECEMBER · LISBON · EDITION').toUpperCase(), {
        position: 'absolute',
        right: 48,
        top: 424,
        width: 250,
        color: theme.ink,
        fontSize: 9,
        lineHeight: 1,
        textAlign: 'center',
        ...fontRole('label', spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, 'right_note', 'Twice a month, ten strangers, one cook,\none long table. By application.'), {
        position: 'absolute',
        right: 48,
        top: 453,
        width: 250,
        color: theme.ink,
        fontSize: 12,
        lineHeight: 1.35,
        textAlign: 'center',
        whiteSpace: 'pre-line',
        ...fontRole('body', spec, { fontWeight: 600 })
      }),
      TextBlock(text(spec, 'page', '01 / 08'), {
        position: 'absolute',
        right: 35,
        bottom: 13,
        color: theme.ink,
        fontSize: 8,
        ...fontRole('metric', spec, { fontWeight: 700 })
      })
    ]
  )
}
