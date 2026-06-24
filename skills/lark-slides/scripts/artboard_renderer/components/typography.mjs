export const REQUIRED_FONT_ROLES = ['display', 'body', 'label', 'metric']

function roleOverrides(spec = {}) {
  const roles = spec.theme?.typography?.font_roles
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

export function fontRole(role, spec = {}, fallback = {}) {
  const aliases = fontRoleAliasesFromTheme(spec)
  const family = aliases[role] || `SVGlide${role.charAt(0).toUpperCase()}${role.slice(1)}`
  return { fontFamily: family, ...fallback }
}

export function withFontRole(style = {}, role, spec = {}) {
  return { ...style, ...fontRole(role, spec) }
}
