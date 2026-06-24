import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'product-ribbon'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'sakura-chroma',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/sakura-chroma-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    paper: source.background || '#F1E6CB',
    ink: source.text || '#3A2516',
    red: source.red || '#E5392A',
    pink: source.primary || '#E54489',
    orange: source.orange || '#F09131',
    green: source.green || '#3D9F47',
    blue: source.blue || '#3F8BC4',
    yellow: source.panel || '#F0BC2A'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function petalCluster(theme) {
  const colors = [theme.red, theme.blue, theme.green, theme.orange, theme.yellow]
  return box(
    { position: 'absolute', left: 34, top: 20, width: 205, height: 154 },
    colors.map((color, index) =>
      box({
        position: 'absolute',
        left: [0, 54, 100, 28, 70][index],
        top: [44, 0, 38, 82, 82][index],
        width: [96, 84, 96, 74, 62][index],
        height: [94, 84, 96, 74, 62][index],
        borderRadius: 999,
        backgroundColor: color
      })
    )
  )
}

function ribbon(theme, top, color, width, offset, height = 58) {
  return box({
    position: 'absolute',
    left: 460 + offset,
    top,
    width,
    height,
    backgroundColor: color,
    transform: 'skewY(-12deg)'
  })
}

function checkbox(theme, label, top, checked) {
  return box(
    { position: 'absolute', right: 78, top, width: 110, height: 18, flexDirection: 'row', alignItems: 'center' },
    [
      box({
        width: 10,
        height: 10,
        borderWidth: 1.5,
        borderColor: theme.ink,
        backgroundColor: checked ? theme.ink : 'transparent',
        marginRight: 8
      }),
      TextBlock(label.toUpperCase(), {
        color: theme.ink,
        ...fontRole('label', null, { fontWeight: 900 }),
        fontSize: 11,
        lineHeight: 1
      })
    ]
  )
}

export function renderProductRibbon(spec) {
  const theme = colors(spec)
  const title = text(spec, 'title', 'T-26')
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
      petalCluster(theme),
      TextBlock(text(spec, 'brand', 'tape\ngarden').toLowerCase(), {
        position: 'absolute',
        left: 230,
        top: 48,
        width: 120,
        color: theme.ink,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 30,
        lineHeight: 0.82,
        whiteSpace: 'pre-wrap'
      }),
      TextBlock(text(spec, 'edition', 'CATALOGUE NO. 7').toUpperCase(), {
        position: 'absolute',
        left: 231,
        top: 104,
        width: 170,
        color: theme.ink,
        ...fontRole('label', spec, { fontWeight: 900 }),
        fontSize: 10,
      }),
      Title(title, {
        position: 'absolute',
        left: 34,
        top: 160,
        width: 250,
        color: theme.ink,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 106,
        lineHeight: 0.86
      }),
      ribbon(theme, 90, theme.pink, 560, 0),
      ribbon(theme, 110, theme.orange, 560, -20),
      ribbon(theme, 132, theme.yellow, 650, -8),
      ribbon(theme, 154, theme.green, 650, 2),
      ribbon(theme, 176, theme.blue, 700, -12),
      checkbox(theme, 'Color', 174, true),
      checkbox(theme, 'Lo-Fi', 218, true),
      checkbox(theme, 'Stereo', 262, false),
      checkbox(theme, 'LP', 306, false),
      TextBlock(text(spec, 'subtitle', 'SUPERCATALOG').toUpperCase(), {
        position: 'absolute',
        left: 34,
        bottom: 86,
        width: 364,
        backgroundColor: theme.pink,
        color: theme.paper,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 40,
        lineHeight: 1,
        padding: '6px 16px 8px'
      }),
      box({ position: 'absolute', left: 34, right: 34, bottom: 78, height: 1, backgroundColor: theme.ink }),
      TextBlock(text(spec, 'footer_left', '限定版  made in matsumoto     N.R. :  ■ ON   □ OFF'), {
        position: 'absolute',
        left: 34,
        bottom: 36,
        width: 360,
        color: theme.ink,
        ...fontRole('body', spec, { fontWeight: 800 }),
        fontSize: 8,
      }),
      box({ position: 'absolute', right: 106, bottom: 24, width: 60, height: 26, backgroundColor: theme.red, alignItems: 'center', justifyContent: 'center' }, [
        TextBlock(text(spec, 'stamp', 'AS SEEN ON\nTG').toUpperCase(), {
          color: theme.paper,
          ...fontRole('label', spec, { fontWeight: 900 }),
          fontSize: 7,
          lineHeight: 1.1,
          textAlign: 'center',
          whiteSpace: 'pre-wrap'
        })
      ]),
      TextBlock(text(spec, 'page', '01 / 08'), {
        position: 'absolute',
        right: 20,
        bottom: 12,
        width: 70,
        color: theme.ink,
        textAlign: 'right',
        ...fontRole('metric', spec, { fontWeight: 900 }),
        fontSize: 7
      })
    ]
  )
}
