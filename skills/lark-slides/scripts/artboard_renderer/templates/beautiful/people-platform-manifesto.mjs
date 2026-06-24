import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'people-platform-manifesto'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: 'peoples-platform',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/peoples-platform-1.png'
}

function colors(spec) {
  return {
    blue: '#322AE8',
    orange: '#FF7A3D',
    cream: '#F6EACD',
    white: '#FFFFFF'
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

export function renderPeoplePlatformManifesto(spec) {
  const theme = colors(spec)
  const platforms = list(spec, 'platforms', ['Prepared by the team', 'May 2026', 'Version 01'])
  return box({ width: 960, height: 540, position: 'relative', backgroundColor: theme.blue, overflow: 'hidden' }, [
    box({ position: 'absolute', left: 42, top: 42, right: 42, bottom: 42, borderWidth: 3, borderColor: theme.cream }),
    TextBlock(text(spec, 'eyebrow', 'STRATEGIC REVIEW · INTERNAL').toUpperCase(), {
      position: 'absolute',
      left: 392,
      top: 66,
      color: theme.cream,
      fontSize: 8,
      letterSpacing: 1.4,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    Title(text(spec, 'title', 'QUARTERLY\nREVIEW').toUpperCase(), {
      position: 'absolute',
      left: 161,
      top: 172,
      width: 660,
      color: theme.cream,
      fontSize: 67,
      lineHeight: 0.82,
      whiteSpace: 'pre-line',
      ...fontRole('display', spec, { fontWeight: 900 })
    }),
    Title(text(spec, 'title', 'QUARTERLY\nREVIEW').toUpperCase(), {
      position: 'absolute',
      left: 153,
      top: 164,
      width: 660,
      color: theme.orange,
      fontSize: 67,
      lineHeight: 0.82,
      whiteSpace: 'pre-line',
      ...fontRole('display', spec, { fontWeight: 900 })
    }),
    TextBlock(text(spec, 'subtitle', 'A PRESENTATION TEMPLATE').toUpperCase(), {
      position: 'absolute',
      left: 265,
      top: 326,
      color: theme.cream,
      fontSize: 24,
      ...fontRole('body', spec, { fontWeight: 900 })
    }),
    TextBlock(platforms.join('  ·  ').toUpperCase(), {
      position: 'absolute',
      left: 331,
      top: 371,
      color: theme.cream,
      fontSize: 8,
      letterSpacing: 1.1,
      ...fontRole('label', spec, { fontWeight: 700 })
    }),
    TextBlock(text(spec, 'stamp', 'VOL. 01').toUpperCase(), {
      position: 'absolute',
      right: 67,
      top: 66,
      color: theme.cream,
      fontSize: 10,
      ...fontRole('metric', spec, { fontWeight: 700 })
    })
  ])
}
