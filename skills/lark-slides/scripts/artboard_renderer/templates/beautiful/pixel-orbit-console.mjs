import { TextBlock, Title, box } from '../../components/primitives.mjs'
import { fontRole } from '../../components/typography.mjs'

export const templateId = 'pixel-orbit-console'

export const rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: 'needs_review',
  renderer_stage: 'dedicated_sample',
  default_selectable: false,
  selection_scope: 'experimental',
  source_family: '8-bit-orbit',
  required_font_roles: ['display', 'body', 'label', 'metric'],
  reference_screenshot: 'beautiful-html-templates/screenshots/8-bit-orbit-1.png'
}

function colors(spec) {
  const source = spec.theme?.colors || {}
  return {
    void: source.background || '#0A0E27',
    navy: source.panel || '#0F1B3D',
    cyan: source.primary || '#5EDCF4',
    pink: source.accent || '#F0A6CA',
    yellow: source.yellow || '#F4D03F',
    lavender: source.muted || '#E2D5F2',
    grid: source.grid || '#1B2B55'
  }
}

function text(spec, key, fallback = '') {
  const value = spec.content?.[key]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function list(spec, key, fallback = []) {
  const value = spec.content?.[key]
  if (!Array.isArray(value)) return fallback
  const cleaned = value.filter((item) => typeof item === 'string' && item.trim()).map((item) => item.trim())
  return cleaned.length ? cleaned : fallback
}

function grid(theme) {
  const vertical = Array.from({ length: 31 }).map((_, index) =>
    box({
      position: 'absolute',
      left: index * 32,
      top: 0,
      width: 1,
      height: 540,
      backgroundColor: theme.grid,
      opacity: index % 5 === 0 ? 0.34 : 0.18
    })
  )
  const horizontal = Array.from({ length: 19 }).map((_, index) =>
    box({
      position: 'absolute',
      left: 0,
      top: index * 30,
      width: 960,
      height: 1,
      backgroundColor: theme.grid,
      opacity: index % 4 === 0 ? 0.32 : 0.15
    })
  )
  return [...vertical, ...horizontal]
}

function stars(theme) {
  const points = [
    [45, 54, 5, theme.yellow],
    [142, 95, 3, theme.pink],
    [245, 28, 3, theme.yellow],
    [402, 16, 3, theme.pink],
    [474, 58, 4, theme.yellow],
    [641, 75, 3, theme.cyan],
    [736, 24, 3, theme.yellow],
    [884, 86, 5, theme.yellow],
    [192, 242, 3, theme.cyan],
    [342, 122, 3, theme.yellow],
    [502, 318, 4, theme.pink],
    [676, 260, 3, theme.cyan],
    [758, 120, 3, theme.pink],
    [916, 162, 4, theme.cyan],
    [60, 397, 3, theme.pink],
    [214, 486, 4, theme.pink],
    [398, 446, 5, theme.yellow],
    [552, 356, 4, theme.yellow],
    [678, 508, 4, theme.cyan],
    [816, 442, 3, theme.yellow],
    [928, 372, 3, theme.cyan]
  ]
  return points.map(([left, top, size, color]) =>
    box({ position: 'absolute', left, top, width: size, height: size, backgroundColor: color, opacity: 0.78 })
  )
}

function pixelTitle(value, top, theme, spec) {
  return [
    Title(value, {
      position: 'absolute',
      left: 394,
      top: top + 7,
      width: 260,
      color: theme.navy,
      fontSize: 58,
      lineHeight: 0.88,
      textAlign: 'center',
      ...fontRole('display', spec, { fontWeight: 900 })
    }),
    Title(value, {
      position: 'absolute',
      left: 390,
      top: top + 5,
      width: 260,
      color: theme.yellow,
      fontSize: 58,
      lineHeight: 0.88,
      textAlign: 'center',
      ...fontRole('display', spec, { fontWeight: 900 })
    }),
    Title(value, {
      position: 'absolute',
      left: 384,
      top,
      width: 260,
      color: theme.cyan,
      fontSize: 58,
      lineHeight: 0.88,
      textAlign: 'center',
      ...fontRole('display', spec, { fontWeight: 900 })
    })
  ]
}

export function renderPixelOrbitConsole(spec) {
  const theme = colors(spec)
  const title = text(spec, 'title', '8-BIT ORBIT').toUpperCase()
  const words = title.split(/\s+/)
  const lineOne = words.slice(0, Math.ceil(words.length / 2)).join(' ') || '8-BIT'
  const lineTwo = words.slice(Math.ceil(words.length / 2)).join(' ') || 'ORBIT'
  const chips = list(spec, 'chips', ['10 SLIDES', 'CSS NATIVE', 'ZERO DEPENDENCIES']).slice(0, 3)
  return box(
    {
      width: 960,
      height: 540,
      position: 'relative',
      backgroundColor: theme.void,
      color: theme.lavender,
      overflow: 'hidden'
    },
    [
      box({ position: 'absolute', left: 0, top: 0, width: 960, height: 540, backgroundColor: theme.navy, opacity: 0.06 }),
      box({ position: 'absolute', left: 0, top: 122, width: 318, height: 332, backgroundColor: '#0A1228', opacity: 0.52 }),
      box({ position: 'absolute', left: 520, top: 0, width: 440, height: 540, backgroundColor: '#112144', opacity: 0.28 }),
      box({ position: 'absolute', left: 0, top: 392, width: 960, height: 148, backgroundColor: '#080A25', opacity: 0.22 }),
      ...grid(theme),
      ...stars(theme),
      TextBlock(text(spec, 'eyebrow', 'P I X E L   P E R F E C T   P R E S E N T A T I O N   S Y S T E M'), {
        position: 'absolute',
        left: 218,
        top: 148,
        width: 540,
        color: theme.pink,
        fontSize: 8,
        lineHeight: 1,
        textAlign: 'center',
        ...fontRole('label', spec, { fontWeight: 700 })
      }),
      ...pixelTitle(lineOne, 178, theme, spec),
      ...pixelTitle(lineTwo, 246, theme, spec),
      TextBlock(text(spec, 'subtitle', 'A retro-futuristic deck engine for bold storytellers.'), {
        position: 'absolute',
        left: 348,
        top: 330,
        width: 300,
        color: theme.lavender,
        fontSize: 13,
        lineHeight: 1.7,
        textAlign: 'center',
        ...fontRole('body', spec, { fontWeight: 500 })
      }),
      box(
        { position: 'absolute', left: 374, top: 376, flexDirection: 'row', gap: 8 },
        chips.map((chip) =>
          TextBlock(chip.toUpperCase(), {
            height: 18,
            minWidth: Math.max(52, chip.length * 8),
            borderWidth: 1,
            borderColor: theme.yellow,
            padding: '3px 10px',
            color: theme.yellow,
            fontSize: 7,
            lineHeight: 1,
            textAlign: 'center',
            ...fontRole('label', spec, { fontWeight: 800 })
          })
        )
      ),
      box(
        { position: 'absolute', right: 14, top: 214, flexDirection: 'column', gap: 8 },
        Array.from({ length: 10 }).map((_, index) =>
          box({
            width: 7,
            height: 7,
            borderWidth: 1,
            borderColor: theme.cyan,
            backgroundColor: index === 0 ? theme.cyan : theme.void
          })
        )
      ),
      TextBlock(text(spec, 'page', '01 / 10'), {
        position: 'absolute',
        left: 451,
        bottom: 17,
        width: 80,
        color: theme.cyan,
        fontSize: 8,
        lineHeight: 1,
        textAlign: 'center',
        ...fontRole('metric', spec, { fontWeight: 700 })
      }),
      TextBlock(text(spec, 'hint', 'USE KEYS + DOWN').toUpperCase(), {
        position: 'absolute',
        right: 15,
        bottom: 15,
        width: 95,
        color: theme.cyan,
        fontSize: 6,
        lineHeight: 1,
        textAlign: 'right',
        opacity: 0.72,
        ...fontRole('label', spec, { fontWeight: 700 })
      })
    ]
  )
}
