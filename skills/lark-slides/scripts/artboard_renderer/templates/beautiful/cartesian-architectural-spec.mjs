import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'architectural-spec'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'cartesian',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/cartesian-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    paper: source.background || '#EDE8E0',
    ink: source.text || '#1A1A1A',
    muted: source.muted || '#5A5A5A',
    line: source.line || '#B8B0A4',
    accent: source.accent || '#8A8178'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function navButton(theme, spec, left, label) {
  return box(
    {
      position: 'absolute',
      left,
      bottom: 22,
      width: 20,
      height: 20,
      borderWidth: 1,
      borderColor: theme.line,
      alignItems: 'center',
      justifyContent: 'center'
    },
    [
      TextBlock(label, {
        color: theme.ink,
        fontSize: 9,
        lineHeight: 1,
        textAlign: 'center',
        ...fontRole('metric', spec, { fontWeight: 700 })
      })
    ]
  )
}

export function renderCartesianArchitecturalSpec(spec) {
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
      TextBlock(text(spec, 'eyebrow', 'PRESENTATION TEMPLATE').toUpperCase(), {
        position: 'absolute',
        left: 38,
        top: 214,
        color: theme.accent,
        fontSize: 7,
        lineHeight: 1,
        ...fontRole('label', spec, { fontWeight: 700 })
      }),
      Title(text(spec, 'title', 'Cartesian'), {
        position: 'absolute',
        left: 38,
        top: 246,
        width: 410,
        color: theme.ink,
        fontSize: 52,
        lineHeight: 1,
        ...fontRole('display', spec, { fontWeight: 400 })
      }),
      TextBlock(text(spec, 'subtitle', 'A minimalist framework for strategic narratives. Clean geometry meets editorial refinement.'), {
        position: 'absolute',
        left: 38,
        top: 300,
        width: 380,
        color: theme.muted,
        fontSize: 12,
        lineHeight: 1.45,
        ...fontRole('body', spec, { fontWeight: 600 })
      }),
      box({ position: 'absolute', right: 48, top: 198, width: 288, height: 288, borderRadius: 144, borderWidth: 1, borderColor: theme.line, opacity: 0.72 }),
      box({ position: 'absolute', right: 76, top: 226, width: 232, height: 232, borderRadius: 116, borderWidth: 1, borderColor: theme.line, borderStyle: 'dashed', opacity: 0.56 }),
      box(
        { position: 'absolute', right: 20, top: 222, flexDirection: 'column', gap: 6 },
        Array.from({ length: 10 }).map((_, index) =>
          box({ width: 4, height: 4, borderRadius: 2, backgroundColor: index === 0 ? theme.ink : theme.line })
        )
      ),
      navButton(theme, spec, 29, '<'),
      navButton(theme, spec, 57, '>'),
      TextBlock(text(spec, 'page', '01 / 10'), {
        position: 'absolute',
        right: 30,
        bottom: 22,
        color: theme.accent,
        fontSize: 7,
        ...fontRole('metric', spec, { fontWeight: 500 })
      })
    ]
  )
}
