import { evaluationRendererContract, evaluationTemplateIds, renderEvaluationBeautifulStub } from './evaluation-stub.mjs'
import { renderExecutiveDashboard, rendererContract as executiveDashboardContract } from './executive-dashboard.mjs'

const DEDICATED_RENDERERS = new Map([
  [
    executiveDashboardContract.template_id,
    {
      contract: executiveDashboardContract,
      render: renderExecutiveDashboard
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
