import fs from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { renderTree } from './templates/p0-templates.mjs'

const SATORI_VERSION = '0.26.0'
const RESVG_VERSION = '2.6.2'
const DEFAULT_FONT_FAMILY = 'SVGlideDefault'
const DEFAULT_FONT_CANDIDATES = [
  '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
  '/System/Library/Fonts/Supplemental/Arial.ttf',
  '/System/Library/Fonts/Supplemental/Verdana.ttf',
  '/System/Library/Fonts/Supplemental/Trebuchet MS.ttf',
  '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
  '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
  'C:\\Windows\\Fonts\\arial.ttf'
]

async function pathExists(candidate) {
  try {
    await fs.access(candidate)
    return true
  } catch {
    return false
  }
}

async function resolveFontPath() {
  if (process.env.SVGLIDE_SATORI_FONT_PATH) {
    return process.env.SVGLIDE_SATORI_FONT_PATH
  }
  for (const candidate of DEFAULT_FONT_CANDIDATES) {
    if (await pathExists(candidate)) {
      return candidate
    }
  }
  throw new Error(
    'no usable Satori font found; set SVGLIDE_SATORI_FONT_PATH to a .ttf/.otf font available on this machine'
  )
}

async function loadFont() {
  const fontPath = await resolveFontPath()
  const data = await fs.readFile(fontPath)
  return { name: DEFAULT_FONT_FAMILY, data, weight: 400, style: 'normal', path: fontPath }
}

async function loadSatori() {
  try {
    return (await import('satori')).default
  } catch (error) {
    console.error('satori dependency is not available in this adapter runtime')
    console.error('development fix: run pnpm install --frozen-lockfile in skills/lark-slides/scripts/artboard_renderer')
    console.error('release fix: install satori as an external runtime dependency before running dist/render.mjs --check-runtime')
    console.error(String(error?.message || error))
    process.exit(3)
  }
}

async function loadResvg() {
  try {
    return (await import('@resvg/resvg-js')).Resvg
  } catch (error) {
    console.error('@resvg/resvg-js native dependency is not available in this adapter runtime')
    console.error('fix: run pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile')
    console.error('release fix: install the platform-native @resvg/resvg-js package before running dist/render.mjs --check-runtime')
    console.error(String(error?.message || error))
    process.exit(4)
  }
}

async function checkRuntime() {
  await loadSatori()
  const Resvg = await loadResvg()
  const font = await loadFont()
  const probe = '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="#000"/></svg>'
  new Resvg(probe).render().asPng()
  console.log(JSON.stringify({ ok: true, renderer: 'satori-resvg', satori_version: SATORI_VERSION, resvg_version: RESVG_VERSION, font_path: font.path }))
}

function serializeObservation(node) {
  const props = node?.props || {}
  const safeProps = {}
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith('data-') && ['string', 'number', 'boolean'].includes(typeof value)) {
      safeProps[key] = value
    }
  }
  return {
    left: node?.left,
    top: node?.top,
    width: node?.width,
    height: node?.height,
    type: node?.type,
    key: node?.key,
    textContent: node?.textContent,
    props: safeProps
  }
}

async function main() {
  const [, , inputPath, outputPath, pngPath, metadataPath, observationsPath] = process.argv
  if (inputPath === '--check-runtime') {
    await checkRuntime()
    return
  }
  if (!inputPath || !outputPath) {
    console.error('usage: node render.mjs <canvas-spec.json> <output.svg> [output.png] [metadata.json]')
    process.exit(2)
  }
  const satori = await loadSatori()
  const Resvg = await loadResvg()
  const spec = JSON.parse(await fs.readFile(inputPath, 'utf8'))
  const font = await loadFont()
  const observations = []
  const svg = await satori(renderTree(spec), {
    width: 960,
    height: 540,
    embedFont: false,
    fonts: [font],
    onNodeDetected: (node) => {
      observations.push(serializeObservation(node))
    }
  })
  await fs.mkdir(path.dirname(outputPath), { recursive: true })
  await fs.writeFile(outputPath, svg)
  let pngBytes = null
  if (pngPath) {
    pngBytes = new Resvg(svg, {
      fitTo: { mode: 'width', value: 960 },
      font: { loadSystemFonts: true }
    }).render().asPng()
    await fs.mkdir(path.dirname(pngPath), { recursive: true })
    await fs.writeFile(pngPath, pngBytes)
  }
  if (metadataPath) {
    await fs.mkdir(path.dirname(metadataPath), { recursive: true })
    await fs.writeFile(
      metadataPath,
      JSON.stringify(
        {
          node_version: process.version,
          satori_version: SATORI_VERSION,
          resvg_version: RESVG_VERSION,
          font_path: font.path,
          png_bytes: pngBytes ? pngBytes.length : null
        },
        null,
        2
      ) + '\n'
    )
  }
  if (observationsPath) {
    await fs.mkdir(path.dirname(observationsPath), { recursive: true })
    await fs.writeFile(
      observationsPath,
      JSON.stringify(
        {
          version: 'svglide-node-observations/v1',
          observation_source: 'satori_on_node_detected',
          nodes: observations
        },
        null,
        2
      ) + '\n'
    )
  }
}

main()
