import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'dense-panel-grid'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'neo-grid-bold',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/neo-grid-bold-1.png'
}

function colors(spec) {
  return {
    black: '#0A0A0A',
    neon: '#E6FF3D',
    paper: '#F5F4EF',
    muted: '#464646'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function list(spec, key, fallback = []) {
  const value = spec.content?.[key]
  return Array.isArray(value) && value.length ? value : fallback
}

export function renderDensePanelGrid(spec) {
  const theme = colors(spec)
  const metrics = list(spec, 'metrics', ['THE FUTURE OF DATA-DRIVEN FINANCE', 'Q2 2026 DIGITS'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.paper, overflow: 'hidden' }, [
    box({ position: 'absolute', left: 0, top: 0, width: 255, height: 540, backgroundColor: theme.black }),
    box({ position: 'absolute', left: 36, top: 42, width: 168, height: 376, borderWidth: 1, borderColor: '#1F1F1F' }),
    box({ position: 'absolute', left: 72, top: 104, width: 96, height: 1, backgroundColor: '#2A2A2A' }),
    box({ position: 'absolute', left: 72, top: 252, width: 96, height: 1, backgroundColor: '#2A2A2A' }),
    box({ position: 'absolute', left: 72, top: 400, width: 96, height: 1, backgroundColor: '#2A2A2A' }),
    box({ position: 'absolute', right: 0, top: 0, width: 308, height: 230, backgroundColor: theme.black }),
    box({ position: 'absolute', right: 74, top: 54, width: 140, height: 120, borderWidth: 1, borderColor: '#202020' }),
    box({ position: 'absolute', right: 112, top: 102, width: 64, height: 1, backgroundColor: '#2B2B2B' }),
    box({ position: 'absolute', right: 112, top: 132, width: 64, height: 1, backgroundColor: '#2B2B2B' }),
    box({ position: 'absolute', left: 256, top: 0, width: 390, height: 540, backgroundColor: theme.neon }),
    box({ position: 'absolute', left: 278, top: 24, width: 38, height: 38, flexDirection: 'row', flexWrap: 'wrap' },
      Array.from({ length: 16 }).map((_, index) => box({ width: 8, height: 8, marginRight: 1, marginBottom: 1, backgroundColor: index % 2 ? theme.neon : theme.black }))
    ),
    box({ position: 'absolute', right: 356, bottom: 64, width: 42, height: 42, flexDirection: 'row', flexWrap: 'wrap' },
      Array.from({ length: 9 }).map((_, index) => box({ width: 10, height: 10, marginRight: 2, marginBottom: 2, backgroundColor: index % 2 ? theme.neon : theme.black }))
    ),
    Title(text(spec, 'title', metrics[0] || 'THE FUTURE OF DATA-DRIVEN FINANCE').toUpperCase(), {
      position: 'absolute',
      left: 285,
      top: 305,
      width: 292,
      color: theme.black,
      lineHeight: 0.94,
      ...fontRole('display', spec, { fontSize: 24, fontWeight: 900, textTransform: 'none' })
    }),
    TextBlock(text(spec, 'eyebrow', '08 / 13'), {
      position: 'absolute',
      left: 20,
      bottom: 48,
      color: theme.paper,
      ...fontRole('metric', spec, { fontSize: 8, fontWeight: 600 })
    }),
    TextBlock((metrics[1] || 'Q2 DIGITS').toUpperCase(), {
      position: 'absolute',
      right: 32,
      bottom: 42,
      color: theme.black,
      lineHeight: 1.25,
      ...fontRole('label', spec, { fontSize: 9, fontWeight: 700 })
    }),
    TextBlock(text(spec, 'subtitle', 'All rights reserved.'), {
      position: 'absolute',
      right: 40,
      bottom: 25,
      color: theme.muted,
      ...fontRole('body', spec, { fontSize: 7, fontWeight: 400 })
    })
  ])
}
