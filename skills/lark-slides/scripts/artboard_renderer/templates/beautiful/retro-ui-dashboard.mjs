import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'retro-ui-dashboard'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'retro-windows',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/retro-windows-1.png'
}

function colors(spec) {
  return {
    desk: '#8B8B87',
    window: '#D8D4C7',
    blue: '#1100A8',
    ink: '#202020'
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

export function renderRetroUiDashboard(spec) {
  const theme = colors(spec)
  const panels = list(spec, 'panels', ['Build status: OK', 'Open issues: 12', 'Owner: Platform'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.desk, overflow: 'hidden' }, [
    box({ position: 'absolute', left: 338, top: 12, width: 326, height: 472, backgroundColor: theme.window, borderWidth: 2, borderColor: theme.ink, flexDirection: 'column' }, [
      box({ width: '100%', height: 18, backgroundColor: theme.blue, flexDirection: 'row', alignItems: 'center', paddingLeft: 8 }, [
        TextBlock(text(spec, 'window_title', 'SVGLIDE.EXE'), { color: '#FFFFFF', fontSize: 8, ...fontRole('label', spec, { fontWeight: 700 }) })
      ]),
      box({ flex: 1, alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }, [
        TextBlock('★', { color: theme.ink, fontSize: 16, marginBottom: 38, ...fontRole('metric', spec, { fontWeight: 900 }) }),
        Title(text(spec, 'title', 'QUARTERLY OVERVIEW').toUpperCase(), { color: theme.blue, fontSize: 18, lineHeight: 1, marginBottom: 12, ...fontRole('display', spec, { fontWeight: 900 }) }),
        TextBlock(text(spec, 'subtitle', 'Compact product status window.'), { width: 220, textAlign: 'center', color: theme.ink, fontSize: 9, lineHeight: 1.3, marginBottom: 18, ...fontRole('body', spec) }),
        ...panels.slice(0, 3).map((item) => TextBlock(item, { width: 206, backgroundColor: '#F4F1E8', borderWidth: 1, borderColor: theme.ink, padding: '4px 6px', color: theme.ink, fontSize: 8, marginBottom: 5, ...fontRole('label', spec, { fontWeight: 600 }) }))
      ])
    ]),
    TextBlock(text(spec, 'status', 'READY'), { position: 'absolute', right: 18, bottom: 15, color: '#FFFFFF', fontSize: 8, ...fontRole('metric', spec) })
  ])
}
