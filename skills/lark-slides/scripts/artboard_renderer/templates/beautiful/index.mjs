import { evaluationRendererContract, evaluationTemplateIds, renderEvaluationBeautifulStub } from './evaluation-stub.mjs'
import { renderExecutiveDashboard, rendererContract as executiveDashboardContract } from './executive-dashboard.mjs'
import { renderIntelligenceBrief, rendererContract as intelligenceBriefContract } from './intelligence-brief.mjs'
import { renderPosterStatPunch, rendererContract as posterStatPunchContract } from './poster-stat-punch.mjs'
import { renderCoralMagazineFeature, rendererContract as coralMagazineFeatureContract } from './coral-magazine-feature.mjs'
import { renderSoftEditorialFeature, rendererContract as softEditorialFeatureContract } from './soft-editorial-feature.mjs'
import { renderTritoneEditorialSpread, rendererContract as tritoneEditorialSpreadContract } from './tritone-editorial-spread.mjs'
import { renderPixelOrbitConsole, rendererContract as pixelOrbitConsoleContract } from './pixel-orbit-console.mjs'
import { renderBiennaleProgrammePoster, rendererContract as biennaleProgrammePosterContract } from './biennale-programme-poster.mjs'
import { renderBlockFrameGrid, rendererContract as blockFrameGridContract } from './block-frame-grid.mjs'
import { renderBroadsideEditorialQuote, rendererContract as broadsideEditorialQuoteContract } from './broadside-editorial-quote.mjs'
import { renderCartesianArchitecturalSpec, rendererContract as cartesianArchitecturalSpecContract } from './cartesian-architectural-spec.mjs'
import { renderLongTablePrintedProgram, rendererContract as longTablePrintedProgramContract } from './long-table-printed-program.mjs'
import { renderMonochromeLedgerBriefing, rendererContract as monochromeLedgerBriefingContract } from './monochrome-ledger-briefing.mjs'
import { renderCapsuleCardSystem, rendererContract as capsuleCardSystemContract } from './capsule-card-system.mjs'
import { renderCreativeModeGrid, rendererContract as creativeModeGridContract } from './creative-mode-grid.mjs'
import { renderDaisyWorkshopPlaybook, rendererContract as daisyWorkshopPlaybookContract } from './daisy-workshop-playbook.mjs'
import { renderEmeraldEditorialCover, rendererContract as emeraldEditorialCoverContract } from './emerald-editorial-cover.mjs'
import { renderTrendGridReport, rendererContract as trendGridReportContract } from './trend-grid-report.mjs'
import { renderProductRibbon, rendererContract as productRibbonContract } from './product-ribbon.mjs'
import { renderBrutalistMatrix, rendererContract as brutalistMatrixContract } from './brutalist-matrix.mjs'
import { renderTypeMassPoster, rendererContract as typeMassPosterContract } from './type-mass-poster.mjs'
import { renderSerifStatEditorial, rendererContract as serifStatEditorialContract } from './serif-stat-editorial.mjs'
import { renderGroveOrganicBrief, rendererContract as groveOrganicBriefContract } from './grove-organic-brief.mjs'
import { renderMatMidcenturyBoard, rendererContract as matMidcenturyBoardContract } from './mat-midcentury-board.mjs'
import { renderDensePanelGrid, rendererContract as densePanelGridContract } from './dense-panel-grid.mjs'
import { renderPeoplePlatformManifesto, rendererContract as peoplePlatformManifestoContract } from './people-platform-manifesto.mjs'
import { renderAnnotatedFieldBoard, rendererContract as annotatedFieldBoardContract } from './annotated-field-board.mjs'
import { renderPinkNocturneFeature, rendererContract as pinkNocturneFeatureContract } from './pink-nocturne-feature.mjs'
import { renderPlayfulIndieLaunch, rendererContract as playfulIndieLaunchContract } from './playful-indie-launch.mjs'
import { renderRetroUiDashboard, rendererContract as retroUiDashboardContract } from './retro-ui-dashboard.mjs'
import { renderRetroZineSpread, rendererContract as retroZineSpreadContract } from './retro-zine-spread.mjs'
import { renderStickyWorkshopBoard, rendererContract as stickyWorkshopBoardContract } from './sticky-workshop-board.mjs'
import { renderStencilFieldManual, rendererContract as stencilFieldManualContract } from './stencil-field-manual.mjs'
import { renderVellumScholarBrief, rendererContract as vellumScholarBriefContract } from './vellum-scholar-brief.mjs'

const DEDICATED_RENDERERS = new Map([
  [
    executiveDashboardContract.template_id,
    {
      contract: executiveDashboardContract,
      render: renderExecutiveDashboard
    }
  ],
  [
    intelligenceBriefContract.template_id,
    {
      contract: intelligenceBriefContract,
      render: renderIntelligenceBrief
    }
  ],
  [
    posterStatPunchContract.template_id,
    {
      contract: posterStatPunchContract,
      render: renderPosterStatPunch
    }
  ],
  [
    coralMagazineFeatureContract.template_id,
    {
      contract: coralMagazineFeatureContract,
      render: renderCoralMagazineFeature
    }
  ],
  [
    softEditorialFeatureContract.template_id,
    {
      contract: softEditorialFeatureContract,
      render: renderSoftEditorialFeature
    }
  ],
  [
    tritoneEditorialSpreadContract.template_id,
    {
      contract: tritoneEditorialSpreadContract,
      render: renderTritoneEditorialSpread
    }
  ],
  [
    pixelOrbitConsoleContract.template_id,
    {
      contract: pixelOrbitConsoleContract,
      render: renderPixelOrbitConsole
    }
  ],
  [
    biennaleProgrammePosterContract.template_id,
    {
      contract: biennaleProgrammePosterContract,
      render: renderBiennaleProgrammePoster
    }
  ],
  [
    blockFrameGridContract.template_id,
    {
      contract: blockFrameGridContract,
      render: renderBlockFrameGrid
    }
  ],
  [
    broadsideEditorialQuoteContract.template_id,
    {
      contract: broadsideEditorialQuoteContract,
      render: renderBroadsideEditorialQuote
    }
  ],
  [
    cartesianArchitecturalSpecContract.template_id,
    {
      contract: cartesianArchitecturalSpecContract,
      render: renderCartesianArchitecturalSpec
    }
  ],
  [
    longTablePrintedProgramContract.template_id,
    {
      contract: longTablePrintedProgramContract,
      render: renderLongTablePrintedProgram
    }
  ],
  [
    monochromeLedgerBriefingContract.template_id,
    {
      contract: monochromeLedgerBriefingContract,
      render: renderMonochromeLedgerBriefing
    }
  ],
  [
    capsuleCardSystemContract.template_id,
    {
      contract: capsuleCardSystemContract,
      render: renderCapsuleCardSystem
    }
  ],
  [
    creativeModeGridContract.template_id,
    {
      contract: creativeModeGridContract,
      render: renderCreativeModeGrid
    }
  ],
  [
    daisyWorkshopPlaybookContract.template_id,
    {
      contract: daisyWorkshopPlaybookContract,
      render: renderDaisyWorkshopPlaybook
    }
  ],
  [
    emeraldEditorialCoverContract.template_id,
    {
      contract: emeraldEditorialCoverContract,
      render: renderEmeraldEditorialCover
    }
  ],
  [
    trendGridReportContract.template_id,
    {
      contract: trendGridReportContract,
      render: renderTrendGridReport
    }
  ],
  [
    productRibbonContract.template_id,
    {
      contract: productRibbonContract,
      render: renderProductRibbon
    }
  ],
  [
    brutalistMatrixContract.template_id,
    {
      contract: brutalistMatrixContract,
      render: renderBrutalistMatrix
    }
  ],
  [
    typeMassPosterContract.template_id,
    {
      contract: typeMassPosterContract,
      render: renderTypeMassPoster
    }
  ],
  [
    serifStatEditorialContract.template_id,
    {
      contract: serifStatEditorialContract,
      render: renderSerifStatEditorial
    }
  ],
  [
    groveOrganicBriefContract.template_id,
    {
      contract: groveOrganicBriefContract,
      render: renderGroveOrganicBrief
    }
  ],
  [
    matMidcenturyBoardContract.template_id,
    {
      contract: matMidcenturyBoardContract,
      render: renderMatMidcenturyBoard
    }
  ],
  [
    densePanelGridContract.template_id,
    {
      contract: densePanelGridContract,
      render: renderDensePanelGrid
    }
  ],
  [
    peoplePlatformManifestoContract.template_id,
    {
      contract: peoplePlatformManifestoContract,
      render: renderPeoplePlatformManifesto
    }
  ],
  [
    annotatedFieldBoardContract.template_id,
    {
      contract: annotatedFieldBoardContract,
      render: renderAnnotatedFieldBoard
    }
  ],
  [
    pinkNocturneFeatureContract.template_id,
    {
      contract: pinkNocturneFeatureContract,
      render: renderPinkNocturneFeature
    }
  ],
  [
    playfulIndieLaunchContract.template_id,
    {
      contract: playfulIndieLaunchContract,
      render: renderPlayfulIndieLaunch
    }
  ],
  [
    retroUiDashboardContract.template_id,
    {
      contract: retroUiDashboardContract,
      render: renderRetroUiDashboard
    }
  ],
  [
    retroZineSpreadContract.template_id,
    {
      contract: retroZineSpreadContract,
      render: renderRetroZineSpread
    }
  ],
  [
    stickyWorkshopBoardContract.template_id,
    {
      contract: stickyWorkshopBoardContract,
      render: renderStickyWorkshopBoard
    }
  ],
  [
    stencilFieldManualContract.template_id,
    {
      contract: stencilFieldManualContract,
      render: renderStencilFieldManual
    }
  ],
  [
    vellumScholarBriefContract.template_id,
    {
      contract: vellumScholarBriefContract,
      render: renderVellumScholarBrief
    }
  ]
])

const EVALUATION_RENDERERS = new Map(
  evaluationTemplateIds.map((templateId) => [
    templateId,
    {
      contract: evaluationRendererContract(templateId),
      render: renderEvaluationBeautifulStub
    }
  ])
)

function productionLike(spec = {}) {
  return spec.template_status === 'production' || spec.selection_scope === 'production' || spec.asset_status === 'production'
}

export function dedicatedBeautifulRendererIds() {
  return Array.from(DEDICATED_RENDERERS.keys()).sort()
}

export function beautifulRendererContract(templateId) {
  return DEDICATED_RENDERERS.get(templateId)?.contract || EVALUATION_RENDERERS.get(templateId)?.contract || null
}

export function renderBeautifulTemplate(spec = {}) {
  const templateId = spec.template_id
  const dedicated = DEDICATED_RENDERERS.get(templateId)
  if (dedicated) {
    return dedicated.render(spec)
  }
  const evaluation = EVALUATION_RENDERERS.get(templateId)
  if (evaluation) {
    return evaluation.render(spec, evaluation.contract)
  }
  if (productionLike(spec)) {
    throw new Error(`missing dedicated beautiful renderer for production template_id: ${templateId}`)
  }
  return null
}
