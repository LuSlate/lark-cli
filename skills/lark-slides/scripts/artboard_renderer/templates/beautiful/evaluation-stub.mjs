export const evaluationTemplateIds = []

export function evaluationRendererContract(templateId) {
  return {
    template_id: templateId,
    renderer_id: `artboard_satori.${templateId}`,
    status: 'evaluation',
    renderer_stage: 'evaluation_only',
    default_selectable: false,
    selection_scope: 'evaluation_only'
  }
}

export function renderEvaluationBeautifulStub() {
  return null
}
