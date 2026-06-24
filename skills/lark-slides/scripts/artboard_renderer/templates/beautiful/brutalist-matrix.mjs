import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'brutalist-matrix'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'raw-grid',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/raw-grid-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    black: source.text || '#0A0A0A',
    white: source.surface || '#FFFFFF',
    pink: source.primary || '#F2D4CF',
    green: source.accent || '#E5EDD6'
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

function row(theme, spec, label, index) {
  return box(
    {
      position: 'absolute',
      left: 480,
      top: index * 77,
      width: 480,
      height: 78,
      backgroundColor: index === 2 ? theme.green : theme.white,
      borderBottomWidth: 2,
      borderBottomColor: theme.black,
      flexDirection: 'row',
      alignItems: 'center',
      paddingLeft: 44
    },
    [
      TextBlock('→', { color: theme.black, width: 28, ...fontRole('metric', null, { fontWeight: 900 }), fontSize: 22 }),
      TextBlock(label.toUpperCase(), {
        color: theme.black,
        ...fontRole('body', spec, { fontWeight: 900 }),
        fontSize: 15,
        lineHeight: 1
      })
    ]
  )
}

export function renderBrutalistMatrix(spec) {
  const theme = colors(spec)
  const rows = list(spec, ['cities', 'cells', 'items'], ['San Francisco', 'New York', 'Cupertino', 'Menlo Park', 'Santa Clara', 'Mountain View', 'Sunnyvale']).slice(0, 7)
  return box(
    { width: 960, height: 540, position: 'relative', backgroundColor: theme.white, color: theme.black, overflow: 'hidden' },
    [
      box({ position: 'absolute', left: 0, top: 0, width: 480, height: 540, backgroundColor: theme.pink }),
      box({ position: 'absolute', left: 32, top: 34, width: 24, height: 24, borderWidth: 2, borderColor: theme.black, alignItems: 'center', justifyContent: 'center' }, [
        TextBlock(text(spec, 'mark', 'RG'), { color: theme.black, ...fontRole('label', spec, { fontWeight: 900 }), fontSize: 10 })
      ]),
      TextBlock(text(spec, 'eyebrow', 'RAW GRID').toUpperCase(), {
        position: 'absolute',
        left: 62,
        top: 42,
        width: 140,
        color: theme.black,
        ...fontRole('label', spec, { fontWeight: 900 }),
        fontSize: 10,
      }),
      Title(text(spec, 'title', 'CITIES.\nSTARTUPS.').toUpperCase(), {
        position: 'absolute',
        left: 32,
        top: 232,
        width: 390,
        color: theme.black,
        ...fontRole('display', spec, { fontWeight: 900 }),
        fontSize: 48,
        lineHeight: 0.94,
        whiteSpace: 'pre-wrap'
      }),
      TextBlock(text(spec, 'callout', '→ DISCOVER ALL STARTUPS').toUpperCase(), {
        position: 'absolute',
        left: 32,
        bottom: 32,
        width: 160,
        color: theme.white,
        backgroundColor: theme.black,
        ...fontRole('label', spec, { fontWeight: 900 }),
        fontSize: 7,
        lineHeight: 1,
        padding: '5px 8px'
      }),
      ...rows.map((item, index) => row(theme, spec, item, index))
    ]
  )
}
