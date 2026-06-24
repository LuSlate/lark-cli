import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'ledger-briefing'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'monochrome',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/monochrome-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    paper: source.background || '#FAFADF',
    ink: source.text || '#1A1A16',
    muted: source.muted || '#5E5E54',
    line: source.line || '#1A1A16'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function titleLines(title) {
  const words = (title || 'User Research Synthesis').split(/\s+/).filter(Boolean)
  return {
    first: words.slice(0, 2).join(' ') || 'User Research',
    second: words.slice(2).join(' ') || 'Synthesis'
  }
}

export function renderMonochromeLedgerBriefing(spec) {
  const theme = colors(spec)
  const title = titleLines(text(spec, 'title', 'User Research Synthesis'))
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
      TextBlock(text(spec, 'eyebrow', 'USER RESEARCH SYNTHESIS / [MONTH, YEAR]').toUpperCase(), {
        position: 'absolute',
        right: 109,
        top: 37,
        width: 260,
        color: theme.muted,
        fontSize: 7,
        lineHeight: 1,
        textAlign: 'right',
        ...fontRole('label', spec, { fontWeight: 500 })
      }),
      Title(title.first, {
        position: 'absolute',
        left: 110,
        top: 242,
        width: 520,
        color: theme.ink,
        fontSize: 60,
        lineHeight: 0.92,
        ...fontRole('display', spec, { fontWeight: 200 })
      }),
      Title(title.second, {
        position: 'absolute',
        left: 110,
        top: 322,
        width: 520,
        color: theme.ink,
        fontSize: 60,
        lineHeight: 0.92,
        ...fontRole('display', spec, { fontWeight: 200 })
      }),
      box({ position: 'absolute', left: 110, top: 415, width: 18, height: 1, backgroundColor: theme.ink }),
      TextBlock(text(spec, 'subtitle', 'What we learned from 24 interviews and what it means for the product.'), {
        position: 'absolute',
        left: 110,
        bottom: 82,
        width: 620,
        color: theme.muted,
        fontSize: 14,
        lineHeight: 1.4,
        ...fontRole('body', spec, { fontWeight: 300 })
      }),
      box({ position: 'absolute', left: 110, right: 78, bottom: 50, height: 1, backgroundColor: theme.ink }),
      TextBlock(text(spec, 'footer_left', 'RESEARCH TEAM · [MONTH, YEAR]').toUpperCase(), {
        position: 'absolute',
        left: 110,
        bottom: 34,
        color: theme.muted,
        fontSize: 7,
        ...fontRole('label', spec, { fontWeight: 500 })
      }),
      TextBlock(text(spec, 'footer_right', 'ROUND [N] · INTERNAL').toUpperCase(), {
        position: 'absolute',
        right: 110,
        bottom: 34,
        width: 170,
        color: theme.muted,
        fontSize: 7,
        textAlign: 'right',
        ...fontRole('label', spec, { fontWeight: 500 })
      }),
      TextBlock(text(spec, 'page', '01 / 16'), {
        position: 'absolute',
        right: 18,
        bottom: 9,
        color: theme.muted,
        fontSize: 6,
        ...fontRole('metric', spec, { fontWeight: 500 })
      })
    ]
  )
}
