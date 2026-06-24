export const REQUIRED_FONT_ROLES = ['display', 'body', 'label', 'metric']

function roleOverrides(spec = {}) {
  const safeSpec = spec && typeof spec === 'object' ? spec : {}
  const roles = safeSpec.theme?.typography?.font_roles
  return roles && typeof roles === 'object' ? roles : {}
}

export function fontRoleAliasesFromTheme(spec = {}) {
  const roles = roleOverrides(spec)
  const result = {}
  for (const role of REQUIRED_FONT_ROLES) {
    if (typeof roles[role] === 'string' && roles[role].trim()) {
      result[role] = roles[role].trim()
    }
  }
  return result
}

export function fontRolesFromTheme(spec = {}) {
  const aliases = fontRoleAliasesFromTheme(spec)
  const result = {}
  for (const [role, family] of Object.entries(aliases)) {
    result[role] = { family }
  }
  return result
}

function roleTokenFromTheme(role, spec = {}) {
  const safeSpec = spec && typeof spec === 'object' ? spec : {}
  const tokens = safeSpec.theme?.typography?.role_tokens
  const token = tokens && typeof tokens === 'object' ? tokens[role] : null
  return token && typeof token === 'object' ? token : {}
}

export function typographyRolesFromTheme(spec = {}) {
  const result = {}
  for (const role of REQUIRED_FONT_ROLES) {
    result[role] = roleTokenFromTheme(role, spec)
  }
  return result
}

function textStyleRolesFromTheme(spec = {}) {
  const safeSpec = spec && typeof spec === 'object' ? spec : {}
  const roles = safeSpec.theme?.typography?.text_style_roles
  return roles && typeof roles === 'object' ? roles : {}
}

export function textDecorationPolicyFromTheme(spec = {}) {
  const roles = textStyleRolesFromTheme(spec)
  const policy = roles.text_decoration_policy
  return policy && typeof policy === 'object' ? policy : {}
}

function decorationRequestFromFallback(fallback = {}) {
  const requestedLine = fallback.textDecorationLine || fallback.textDecoration
  if (typeof requestedLine !== 'string') return 'none'
  if (requestedLine.includes('line-through')) return 'line_through'
  if (requestedLine.includes('underline')) return 'underline'
  return 'none'
}

function textDecorationStyle(spec = {}, request = 'none') {
  const policy = textDecorationPolicyFromTheme(spec)
  const underline = policy.underline && typeof policy.underline === 'object' ? policy.underline : {}
  const lineThrough = policy.line_through && typeof policy.line_through === 'object' ? policy.line_through : {}
  const selected = request === 'line_through' ? lineThrough : underline
  if (request === 'none' || selected.style === 'none') {
    return { textDecorationLine: 'none' }
  }
  return {
    textDecorationLine: request === 'line_through' ? 'line-through' : 'underline',
    textDecorationStyle: selected.style || 'solid',
    textDecorationColor: selected.color || 'currentColor',
    textDecorationThickness: selected.thickness || '1px'
  }
}

function tokenStyle(role, spec = {}) {
  const token = roleTokenFromTheme(role, spec)
  const style = {}
  if (typeof token.font_size === 'number') style.fontSize = token.font_size
  if (typeof token.font_weight === 'number') style.fontWeight = token.font_weight
  if (typeof token.line_height === 'number') style.lineHeight = token.line_height
  if (typeof token.letter_spacing === 'number') style.letterSpacing = token.letter_spacing
  if (typeof token.text_transform === 'string' && token.text_transform.includes('uppercase')) style.textTransform = 'uppercase'
  return style
}

export function fontRole(role, spec = {}, fallback = {}) {
  const aliases = fontRoleAliasesFromTheme(spec)
  const family = aliases[role] || `SVGlide${role.charAt(0).toUpperCase()}${role.slice(1)}`
  return { fontFamily: family, ...tokenStyle(role, spec), ...textDecorationStyle(spec, decorationRequestFromFallback(fallback)), ...fallback }
}

export function withFontRole(style = {}, role, spec = {}) {
  return { ...style, ...fontRole(role, spec) }
}
