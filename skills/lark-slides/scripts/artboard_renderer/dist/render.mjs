// render.mjs
import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

// components/primitives.mjs
function node(type, style, children) {
  return { type, props: { style, children } };
}
function box(style, children = []) {
  return node("div", { display: "flex", boxSizing: "border-box", ...style }, children);
}
function TextBlock(value, style = {}) {
  return node(
    "div",
    {
      display: "flex",
      boxSizing: "border-box",
      whiteSpace: "normal",
      ...style
    },
    value
  );
}
function Title(value, style = {}) {
  return TextBlock(value, {
    fontSize: 58,
    fontWeight: 800,
    lineHeight: 1.05,
    ...style
  });
}
function Subtitle(value, style = {}) {
  return TextBlock(value, {
    fontSize: 24,
    fontWeight: 500,
    lineHeight: 1.25,
    ...style
  });
}
function Badge(value, style = {}) {
  return TextBlock(value, {
    fontSize: 18,
    fontWeight: 700,
    ...style
  });
}
function Chip(value, style = {}) {
  return TextBlock(value, {
    minWidth: 92,
    height: 40,
    padding: "8px 15px",
    fontSize: 17,
    fontWeight: 600,
    ...style
  });
}
function StatCard({ index, label, color, textColor, panelColor, style = {} }) {
  return box(
    {
      width: 250,
      minHeight: 126,
      flexDirection: "column",
      backgroundColor: panelColor,
      padding: 22,
      ...style
    },
    [
      TextBlock(String(index).padStart(2, "0"), {
        color,
        fontSize: 18,
        fontWeight: 800,
        marginBottom: 12
      }),
      TextBlock(label, {
        color: textColor,
        fontSize: 21,
        fontWeight: 700,
        lineHeight: 1.18
      })
    ]
  );
}

// templates/beautiful/evaluation-stub.mjs
var evaluationTemplateIds = [];
function evaluationRendererContract(templateId35) {
  return {
    template_id: templateId35,
    renderer_id: `artboard_satori.${templateId35}`,
    status: "evaluation",
    renderer_stage: "evaluation_only",
    default_selectable: false,
    selection_scope: "evaluation_only"
  };
}
function renderEvaluationBeautifulStub() {
  return null;
}

// components/typography.mjs
var REQUIRED_FONT_ROLES = ["display", "body", "label", "metric"];
function roleOverrides(spec = {}) {
  const safeSpec = spec && typeof spec === "object" ? spec : {};
  const roles = safeSpec.theme?.typography?.font_roles;
  return roles && typeof roles === "object" ? roles : {};
}
function fontRoleAliasesFromTheme(spec = {}) {
  const roles = roleOverrides(spec);
  const result = {};
  for (const role of REQUIRED_FONT_ROLES) {
    if (typeof roles[role] === "string" && roles[role].trim()) {
      result[role] = roles[role].trim();
    }
  }
  return result;
}
function fontRolesFromTheme(spec = {}) {
  const aliases = fontRoleAliasesFromTheme(spec);
  const result = {};
  for (const [role, family] of Object.entries(aliases)) {
    result[role] = { family };
  }
  return result;
}
function roleTokenFromTheme(role, spec = {}) {
  const safeSpec = spec && typeof spec === "object" ? spec : {};
  const tokens = safeSpec.theme?.typography?.role_tokens;
  const token = tokens && typeof tokens === "object" ? tokens[role] : null;
  return token && typeof token === "object" ? token : {};
}
function typographyRolesFromTheme(spec = {}) {
  const result = {};
  for (const role of REQUIRED_FONT_ROLES) {
    result[role] = roleTokenFromTheme(role, spec);
  }
  return result;
}
function textStyleRolesFromTheme(spec = {}) {
  const safeSpec = spec && typeof spec === "object" ? spec : {};
  const roles = safeSpec.theme?.typography?.text_style_roles;
  return roles && typeof roles === "object" ? roles : {};
}
function textDecorationPolicyFromTheme(spec = {}) {
  const roles = textStyleRolesFromTheme(spec);
  const policy = roles.text_decoration_policy;
  return policy && typeof policy === "object" ? policy : {};
}
function decorationRequestFromFallback(fallback = {}) {
  const requestedLine = fallback.textDecorationLine || fallback.textDecoration;
  if (typeof requestedLine !== "string") return "none";
  if (requestedLine.includes("line-through")) return "line_through";
  if (requestedLine.includes("underline")) return "underline";
  return "none";
}
function textDecorationStyle(spec = {}, request = "none") {
  const policy = textDecorationPolicyFromTheme(spec);
  const underline = policy.underline && typeof policy.underline === "object" ? policy.underline : {};
  const lineThrough = policy.line_through && typeof policy.line_through === "object" ? policy.line_through : {};
  const selected = request === "line_through" ? lineThrough : underline;
  if (request === "none" || selected.style === "none") {
    return { textDecorationLine: "none" };
  }
  return {
    textDecorationLine: request === "line_through" ? "line-through" : "underline",
    textDecorationStyle: selected.style || "solid",
    textDecorationColor: selected.color || "currentColor",
    textDecorationThickness: selected.thickness || "1px"
  };
}
function tokenStyle(role, spec = {}) {
  const token = roleTokenFromTheme(role, spec);
  const style = {};
  if (typeof token.font_size === "number") style.fontSize = token.font_size;
  if (typeof token.font_weight === "number") style.fontWeight = token.font_weight;
  if (typeof token.line_height === "number") style.lineHeight = token.line_height;
  if (typeof token.letter_spacing === "number") style.letterSpacing = token.letter_spacing;
  if (typeof token.text_transform === "string" && token.text_transform.includes("uppercase")) style.textTransform = "uppercase";
  return style;
}
function fontRole(role, spec = {}, fallback = {}) {
  const aliases = fontRoleAliasesFromTheme(spec);
  const family = aliases[role] || `SVGlide${role.charAt(0).toUpperCase()}${role.slice(1)}`;
  return { fontFamily: family, ...tokenStyle(role, spec), ...textDecorationStyle(spec, decorationRequestFromFallback(fallback)), ...fallback };
}

// templates/beautiful/executive-dashboard.mjs
var templateId = "executive-dashboard";
var rendererContract = {
  template_id: templateId,
  renderer_id: `artboard_satori.${templateId}`,
  status: "production",
  renderer_stage: "closed_loop_sample",
  default_selectable: true,
  selection_scope: "production",
  source_family: "blue-professional",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/blue-professional-1.png"
};
function colors(spec) {
  const source = spec.theme?.colors || {};
  return {
    background: source.background || "#FDFAE7",
    panel: source.panel || "#FFFFFF",
    surface: source.surface || "#F5F7FF",
    primary: source.primary || "#1E2BFA",
    accent: source.accent || "#1E2BFA",
    text: source.text || "#111111",
    muted: source.muted || "#6B6B6B",
    border: source.border || "#D4D8FE"
  };
}
function text(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function renderExecutiveDashboard(spec) {
  const theme = colors(spec);
  const footer = text(spec, "footer", "Q2 2026 \xB7 Confidential");
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.background,
      color: theme.text,
      overflow: "hidden"
    },
    [
      box({
        position: "absolute",
        right: -86,
        top: -56,
        width: 374,
        height: 660,
        backgroundColor: "#E8E7E6",
        transform: "skewX(-10deg)"
      }),
      box({ position: "absolute", left: 0, bottom: 0, width: 96, height: 2, backgroundColor: theme.primary }),
      box({ position: "absolute", left: 77, top: 183, width: 30, height: 2, backgroundColor: theme.primary }),
      TextBlock(text(spec, "eyebrow", "EXECUTIVE REVIEW").toUpperCase(), {
        position: "absolute",
        left: 78,
        top: 178,
        color: theme.primary,
        fontSize: 1,
        letterSpacing: 0,
        ...fontRole("label", spec, { fontWeight: 900 })
      }),
      Title(text(spec, "title", "\u5185\u90E8\u4E1A\u52A1\u590D\u76D8"), {
        position: "absolute",
        left: 77,
        top: 199,
        width: 420,
        color: theme.text,
        fontSize: 38,
        lineHeight: 1.08,
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      TextBlock(text(spec, "subtitle", "\u6307\u6807\u3001\u8BC1\u636E\u4E0E\u884C\u52A8\u8BA1\u5212"), {
        position: "absolute",
        left: 78,
        top: 282,
        width: 440,
        color: theme.muted,
        fontSize: 12,
        lineHeight: 1.35,
        ...fontRole("body", spec)
      }),
      TextBlock(footer, {
        position: "absolute",
        left: 77,
        top: 337,
        width: 220,
        color: theme.muted,
        fontSize: 7,
        lineHeight: 1,
        ...fontRole("label", spec)
      }),
      box(
        { position: "absolute", right: 77, bottom: 63, width: 30, height: 30, flexDirection: "row", flexWrap: "wrap", gap: 5 },
        Array.from({ length: 9 }).map(
          (_, index) => box({ width: 3, height: 3, backgroundColor: theme.primary, opacity: 0.28 })
        )
      ),
      TextBlock("1 / 10", {
        position: "absolute",
        left: 28,
        bottom: 14,
        width: 48,
        color: theme.muted,
        fontSize: 7,
        ...fontRole("metric", spec)
      })
    ]
  );
}

// templates/beautiful/intelligence-brief.mjs
var templateId2 = "intelligence-brief";
var rendererContract2 = {
  template_id: templateId2,
  renderer_id: `artboard_satori.${templateId2}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "signal",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/signal-1.png"
};
function colors2(spec) {
  const source = spec.theme?.colors || {};
  return {
    background: source.background || "#1C2644",
    backgroundAlt: source.surface || "#232F55",
    text: source.text || "#E2DCD0",
    muted: source.muted || "#8A96A8",
    hint: source.hint || "#4E5A6E",
    accent: source.accent || "#C8A870",
    border: source.border || "#2E3D5C"
  };
}
function text2(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list(spec, keys, fallback = []) {
  for (const key of keys) {
    const value = spec.content?.[key];
    if (Array.isArray(value)) {
      const cleaned = value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim());
      if (cleaned.length) return cleaned;
    }
  }
  return fallback;
}
function gridTexture(theme) {
  const lines = [];
  for (let x = 80; x < 960; x += 80) {
    lines.push(box({ position: "absolute", left: x, top: 0, width: 1, height: 540, backgroundColor: theme.hint, opacity: 0.72 }));
  }
  for (let y = 80; y < 540; y += 80) {
    lines.push(box({ position: "absolute", left: 0, top: y, width: 960, height: 1, backgroundColor: theme.hint, opacity: 0.72 }));
  }
  lines.push(box({ position: "absolute", left: 64, top: 64, width: 832, height: 1, backgroundColor: theme.border, opacity: 0.74 }));
  lines.push(box({ position: "absolute", left: 64, bottom: 50, width: 832, height: 1, backgroundColor: theme.border, opacity: 0.7 }));
  return lines;
}
function bracketedTitle(title) {
  const cleaned = title || "Presentation Title";
  if (cleaned.includes("[")) return cleaned;
  const parts = cleaned.split(/\s+/);
  if (parts.length <= 1) return `[${cleaned}]`;
  return `[${parts.slice(0, -1).join(" ")}]
${parts[parts.length - 1]}`;
}
function metadataRow(spec, theme) {
  const left = text2(spec, "eyebrow", "PRIVATE INTELLIGENCE NOTE").toUpperCase();
  const right = text2(spec, "date", "JUNE 2026").toUpperCase();
  return [
    TextBlock(left, {
      position: "absolute",
      left: 64,
      top: 48,
      color: theme.muted,
      fontSize: 7,
      lineHeight: 1,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    TextBlock(right, {
      position: "absolute",
      right: 64,
      top: 48,
      width: 160,
      color: theme.muted,
      fontSize: 7,
      lineHeight: 1,
      textAlign: "right",
      ...fontRole("label", spec, { fontWeight: 700 })
    })
  ];
}
function renderIntelligenceBrief(spec) {
  const theme = colors2(spec);
  const points = list(spec, ["points", "items"], ["Current limitation or source of friction", "Expected improvement or capability", "Decision owner and next signal"]).slice(0, 3);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.background,
      color: theme.text,
      overflow: "hidden"
    },
    [
      ...gridTexture(theme),
      ...metadataRow(spec, theme),
      box({ position: "absolute", left: 64, top: 127, width: 34, height: 1, backgroundColor: theme.accent }),
      Title(bracketedTitle(text2(spec, "title", "Presentation Title")), {
        position: "absolute",
        left: 64,
        top: 147,
        width: 445,
        color: theme.text,
        fontSize: 47,
        lineHeight: 0.94,
        whiteSpace: "pre-wrap",
        ...fontRole("display", spec, { fontWeight: 800 })
      }),
      TextBlock(text2(spec, "subtitle", "A short description of the deck, its purpose, and the decision it supports."), {
        position: "absolute",
        left: 66,
        top: 284,
        width: 360,
        color: theme.muted,
        fontSize: 10,
        lineHeight: 1.55,
        ...fontRole("body", spec)
      }),
      box({
        position: "absolute",
        left: 64,
        top: 344,
        width: 112,
        height: 1,
        backgroundColor: theme.accent,
        opacity: 0.88
      }),
      box(
        {
          position: "absolute",
          right: 68,
          top: 156,
          width: 250,
          flexDirection: "column"
        },
        points.map(
          (point, index) => box(
            {
              minHeight: 52,
              flexDirection: "row",
              borderTopWidth: 1,
              borderTopColor: index === 0 ? theme.accent : theme.border,
              padding: "13px 0"
            },
            [
              TextBlock(String(index + 1).padStart(2, "0"), {
                width: 42,
                color: theme.accent,
                fontSize: 12,
                lineHeight: 1,
                ...fontRole("metric", spec, { fontWeight: 800 })
              }),
              TextBlock(point, {
                flex: 1,
                color: theme.muted,
                fontSize: 9,
                lineHeight: 1.45,
                ...fontRole("body", spec)
              })
            ]
          )
        )
      ),
      TextBlock(text2(spec, "footer_left", "PRIVATE / RESEARCH"), {
        position: "absolute",
        left: 64,
        bottom: 33,
        width: 190,
        color: theme.hint,
        fontSize: 7,
        ...fontRole("label", spec, { fontWeight: 700 })
      }),
      TextBlock(text2(spec, "footer_right", "CONFIDENTIAL"), {
        position: "absolute",
        right: 64,
        bottom: 33,
        width: 160,
        color: theme.hint,
        fontSize: 7,
        textAlign: "right",
        ...fontRole("label", spec, { fontWeight: 700 })
      })
    ]
  );
}

// templates/beautiful/poster-stat-punch.mjs
var templateId3 = "poster-stat-punch";
var rendererContract3 = {
  template_id: templateId3,
  renderer_id: `artboard_satori.${templateId3}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "bold-poster",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/bold-poster-1.png"
};
function colors3(spec) {
  const source = spec.theme?.colors || {};
  return {
    background: source.background || "#FFFFFF",
    paper: source.surface || "#F5F2EF",
    text: source.text || "#1C1410",
    muted: source.muted || "#7B706A",
    red: source.primary || "#D8000F",
    line: source.accent || "#1C1410"
  };
}
function text3(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list2(spec, keys, fallback = []) {
  for (const key of keys) {
    const value = spec.content?.[key];
    if (Array.isArray(value)) {
      const cleaned = value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim());
      if (cleaned.length) return cleaned;
    }
  }
  return fallback;
}
function splitPosterTitle(title) {
  const cleaned = title || "Apex Group Ltd.";
  const words = cleaned.split(/\s+/).filter(Boolean);
  if (words.length >= 3) {
    return {
      top: words[0],
      red: words[1],
      tail: words.slice(2).join(" ")
    };
  }
  if (words.length === 2) {
    return { top: words[0], red: words[1], tail: "Ltd." };
  }
  return { top: cleaned, red: "Group", tail: "Ltd." };
}
function offsetTitle(value, style, theme, spec) {
  return [
    Title(value, {
      ...style,
      left: style.left + 5,
      top: style.top + 5,
      color: theme.text,
      opacity: 0.16,
      ...fontRole("display", spec, { fontWeight: 900 })
    }),
    Title(value, {
      ...style,
      left: style.left + 2,
      top: style.top + 2,
      color: theme.text,
      opacity: 0.22,
      ...fontRole("display", spec, { fontWeight: 900 })
    }),
    Title(value, {
      ...style,
      color: theme.red,
      ...fontRole("display", spec, { fontWeight: 900 })
    })
  ];
}
function renderPosterStatPunch(spec) {
  const theme = colors3(spec);
  const parts = splitPosterTitle(text3(spec, "title", "Apex Group Ltd."));
  const pillars = list2(spec, ["pillars", "items"], ["Regional momentum", "Portfolio expansion", "Operating discipline"]).slice(0, 3);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.background,
      color: theme.text,
      overflow: "hidden"
    },
    [
      TextBlock(text3(spec, "eyebrow", "Q2 Strategy Overview").toUpperCase(), {
        position: "absolute",
        left: 68,
        top: 58,
        width: 240,
        color: theme.muted,
        fontSize: 7,
        lineHeight: 1,
        ...fontRole("label", spec, { fontWeight: 800 })
      }),
      Title(parts.top, {
        position: "absolute",
        left: 66,
        top: 86,
        width: 372,
        color: theme.text,
        fontSize: 48,
        lineHeight: 0.92,
        transform: "rotate(-4deg)",
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      ...offsetTitle(parts.red, {
        position: "absolute",
        left: 65,
        top: 131,
        width: 420,
        fontSize: 58,
        lineHeight: 0.86,
        transform: "rotate(-4deg)"
      }, theme, spec),
      Title(parts.tail, {
        position: "absolute",
        left: 292,
        top: 146,
        width: 274,
        color: theme.text,
        fontSize: 38,
        lineHeight: 0.9,
        transform: "rotate(2deg)",
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      TextBlock(text3(spec, "subtitle", "A confident poster-scale claim for a decision-ready deck."), {
        position: "absolute",
        right: 76,
        bottom: 82,
        width: 278,
        color: theme.text,
        fontSize: 11,
        lineHeight: 1.55,
        textAlign: "right",
        ...fontRole("body", spec)
      }),
      TextBlock(text3(spec, "date", "2026"), {
        position: "absolute",
        right: 76,
        bottom: 54,
        width: 120,
        color: theme.muted,
        fontSize: 8,
        textAlign: "right",
        ...fontRole("label", spec, { fontWeight: 800 })
      }),
      box({ position: "absolute", left: 66, bottom: 64, width: 86, height: 2, backgroundColor: theme.red }),
      box({ position: "absolute", left: 66, bottom: 44, width: 704, height: 2, backgroundColor: theme.red }),
      box(
        {
          position: "absolute",
          left: 382,
          top: 272,
          width: 404,
          flexDirection: "row",
          borderTopWidth: 2,
          borderTopColor: theme.line,
          borderBottomWidth: 2,
          borderBottomColor: theme.line
        },
        pillars.map(
          (pillar, index) => box(
            {
              width: 134,
              minHeight: 94,
              flexDirection: "column",
              borderLeftWidth: index === 0 ? 0 : 1,
              borderLeftColor: theme.line,
              padding: "13px 14px"
            },
            [
              TextBlock(String(index + 1).padStart(2, "0"), {
                color: theme.red,
                fontSize: 17,
                lineHeight: 1,
                marginBottom: 8,
                ...fontRole("metric", spec, { fontWeight: 900 })
              }),
              TextBlock(pillar, {
                color: theme.text,
                fontSize: 10,
                lineHeight: 1.35,
                ...fontRole("body", spec)
              })
            ]
          )
        )
      ),
      TextBlock(text3(spec, "stat", ""), {
        position: "absolute",
        right: 78,
        top: 58,
        width: 160,
        color: theme.red,
        fontSize: 18,
        textAlign: "right",
        ...fontRole("metric", spec, { fontWeight: 900 })
      })
    ]
  );
}

// templates/beautiful/coral-magazine-feature.mjs
var templateId4 = "coral-magazine-feature";
var rendererContract4 = {
  template_id: templateId4,
  renderer_id: `artboard_satori.${templateId4}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "coral",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/coral-1.png"
};
function colors4(spec) {
  const source = spec.theme?.colors || {};
  return {
    coral: source.primary || "#E85D5D",
    coralDark: source.accent || "#C45252",
    cream: source.background || "#F5F0E8",
    creamDark: source.panel || "#E8E0D4",
    ink: source.text || "#1A1A1A",
    gray: source.muted || "#6B6B6B",
    white: "#FFFFFF"
  };
}
function text4(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function coralChevrons(theme) {
  const shapes = [];
  for (let index = -1; index < 7; index += 1) {
    const left = index * 160 + 40;
    shapes.push(box({
      position: "absolute",
      left,
      top: 10,
      width: 28,
      height: 210,
      backgroundColor: theme.coralDark,
      opacity: 0.62,
      transform: "rotate(26deg)"
    }));
    shapes.push(box({
      position: "absolute",
      left: left + 70,
      top: 10,
      width: 28,
      height: 210,
      backgroundColor: theme.coralDark,
      opacity: 0.62,
      transform: "rotate(-26deg)"
    }));
    shapes.push(box({
      position: "absolute",
      left: left + 26,
      top: 58,
      width: 14,
      height: 142,
      backgroundColor: theme.coralDark,
      opacity: 0.42,
      transform: "rotate(26deg)"
    }));
    shapes.push(box({
      position: "absolute",
      left: left + 79,
      top: 58,
      width: 14,
      height: 142,
      backgroundColor: theme.coralDark,
      opacity: 0.42,
      transform: "rotate(-26deg)"
    }));
  }
  return shapes;
}
function renderCoralMagazineFeature(spec) {
  const theme = colors4(spec);
  const title = text4(spec, "title", "Quarterly Strategy Session 2026");
  const titleLines3 = title.toUpperCase().split(/\s+/);
  const first = titleLines3.slice(0, 1).join(" ");
  const second = titleLines3.slice(1, 2).join(" ");
  const third = titleLines3.slice(2).join(" ");
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.cream,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      box(
        { position: "absolute", left: 0, top: 0, width: 960, height: 172, backgroundColor: theme.coral },
        coralChevrons(theme)
      ),
      TextBlock(text4(spec, "eyebrow", "VENTURE").toUpperCase(), {
        position: "absolute",
        left: 50,
        top: 23,
        color: theme.ink,
        ...fontRole("label", spec, { fontWeight: 900 }),
        fontSize: 7,
        letterSpacing: 4
      }),
      Title(first || "QUARTERLY", {
        position: "absolute",
        left: 50,
        top: 197,
        width: 500,
        color: theme.ink,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 43,
        lineHeight: 0.9
      }),
      Title(second || "STRATEGY", {
        position: "absolute",
        left: 50,
        top: 250,
        width: 520,
        color: theme.ink,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 43,
        lineHeight: 0.9
      }),
      Title(third || "SESSION 2026", {
        position: "absolute",
        left: 50,
        top: 305,
        width: 620,
        color: theme.ink,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 43,
        lineHeight: 0.9
      }),
      box({ position: "absolute", left: 50, top: 372, width: 860, height: 1, backgroundColor: theme.creamDark }),
      ...Array.from({ length: 10 }).map(
        (_, index) => box({
          position: "absolute",
          right: 30,
          top: 218 + index * 11,
          width: 5,
          height: 5,
          borderRadius: 3,
          backgroundColor: index === 0 ? theme.coral : theme.white,
          opacity: index === 0 ? 1 : 0.78
        })
      ),
      TextBlock(text4(spec, "location_label", "LOCATION").toUpperCase(), {
        position: "absolute",
        left: 50,
        bottom: 43,
        color: theme.gray,
        ...fontRole("label", spec, { fontWeight: 800 }),
        fontSize: 7,
        letterSpacing: 3
      }),
      TextBlock(text4(spec, "location", "7TH FLOOR").toUpperCase(), {
        position: "absolute",
        left: 50,
        bottom: 24,
        color: theme.ink,
        ...fontRole("body", spec, { fontWeight: 900 }),
        fontSize: 19,
        lineHeight: 1
      }),
      TextBlock(text4(spec, "date", "MAY 15 / 09:00 START").toUpperCase(), {
        position: "absolute",
        right: 50,
        bottom: 44,
        width: 210,
        color: theme.gray,
        textAlign: "right",
        ...fontRole("label", spec, { fontWeight: 800 }),
        fontSize: 7,
        letterSpacing: 2
      }),
      TextBlock(text4(spec, "year", "2026"), {
        position: "absolute",
        right: 50,
        bottom: 24,
        width: 70,
        color: theme.ink,
        textAlign: "right",
        ...fontRole("metric", spec, { fontWeight: 900 }),
        fontSize: 20,
        lineHeight: 1
      }),
      TextBlock("01 / 10", {
        position: "absolute",
        right: 20,
        bottom: 11,
        color: theme.white,
        ...fontRole("metric", spec),
        fontSize: 7
      })
    ]
  );
}

// templates/beautiful/soft-editorial-feature.mjs
var templateId5 = "soft-editorial-feature";
var rendererContract5 = {
  template_id: templateId5,
  renderer_id: `artboard_satori.${templateId5}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "soft-editorial",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/soft-editorial-4.png"
};
function colors5(spec) {
  const source = spec.theme?.colors || {};
  return {
    paper: source.background || "#F2EEDF",
    ink: source.text || "#2A241B",
    inkSoft: source.muted || "#5C5345",
    pink: source.pink || "#E1A4C2",
    lemon: source.lemon || "#D6DD63",
    blush: source.blush || "#E8C9B6",
    sage: source.sage || "#B7C7A8"
  };
}
function text5(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list3(spec, keys, fallback = []) {
  for (const key of keys) {
    const value = spec.content?.[key];
    if (Array.isArray(value)) {
      const cleaned = value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim());
      if (cleaned.length) return cleaned;
    }
  }
  return fallback;
}
function card(theme, spec, { left, color, index, title, subtitle }) {
  return box(
    {
      position: "absolute",
      left,
      top: 100,
      width: 284,
      height: 340,
      flexDirection: "column",
      alignItems: "center",
      backgroundColor: color,
      borderRadius: 18,
      padding: "36px 40px"
    },
    [
      Title(`Insight #${index}`, {
        color: theme.ink,
        fontSize: 33,
        lineHeight: 1,
        textAlign: "center",
        marginBottom: 15,
        ...fontRole("display", spec, { fontWeight: 600 })
      }),
      TextBlock(title, {
        color: theme.ink,
        fontSize: 15,
        lineHeight: 1.2,
        textAlign: "center",
        marginBottom: 24,
        ...fontRole("body", spec, { fontWeight: 800 })
      }),
      TextBlock(subtitle, {
        width: 204,
        height: 74,
        color: theme.ink,
        fontSize: 12,
        lineHeight: 1.35,
        textAlign: "center",
        ...fontRole("body", spec, { fontWeight: 500 })
      })
    ]
  );
}
function renderSoftEditorialFeature(spec) {
  const theme = colors5(spec);
  const cards = list3(spec, ["cards", "items"], [
    "Trust is the onboarding",
    "Power users dread upgrades",
    "Support is product"
  ]).slice(0, 3);
  const descriptions = list3(spec, ["descriptions", "points"], [
    "Customers don't churn on day one because the product is hard.",
    "The people we asked to love new features quietly resent them.",
    "Feature requests often hide a discovery problem."
  ]).slice(0, 3);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      TextBlock(text5(spec, "eyebrow", "Insights"), {
        position: "absolute",
        left: 40,
        top: 34,
        color: theme.ink,
        fontSize: 15,
        ...fontRole("label", spec, { fontWeight: 700 })
      }),
      TextBlock(text5(spec, "section_number", "iv"), {
        position: "absolute",
        right: 40,
        top: 36,
        color: theme.ink,
        fontSize: 12,
        ...fontRole("metric", spec, { fontWeight: 500 })
      }),
      card(theme, spec, { left: 40, color: theme.pink, index: 1, title: cards[0], subtitle: descriptions[0] }),
      card(theme, spec, { left: 338, color: theme.lemon, index: 2, title: cards[1], subtitle: descriptions[1] }),
      card(theme, spec, { left: 636, color: theme.blush, index: 3, title: cards[2], subtitle: descriptions[2] }),
      TextBlock(text5(spec, "date", "April 29, 2026"), {
        position: "absolute",
        left: 40,
        bottom: 31,
        color: theme.inkSoft,
        fontSize: 13,
        ...fontRole("display", spec, { fontWeight: 500 })
      }),
      TextBlock(text5(spec, "footer", "Field Notes \xB7 Vol. III"), {
        position: "absolute",
        right: 40,
        bottom: 31,
        width: 190,
        color: theme.inkSoft,
        fontSize: 13,
        textAlign: "right",
        ...fontRole("display", spec, { fontWeight: 500 })
      })
    ]
  );
}

// templates/beautiful/tritone-editorial-spread.mjs
var templateId6 = "tritone-editorial-spread";
var rendererContract6 = {
  template_id: templateId6,
  renderer_id: `artboard_satori.${templateId6}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "editorial-tri-tone",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/editorial-tri-tone-1.png"
};
function colors6(spec) {
  const source = spec.theme?.colors || {};
  return {
    pink: source.background || "#F2B6C6",
    yellow: source.accent || "#F2D86A",
    burgundy: source.primary || "#7A1F35",
    text: source.text || "#7A1F35"
  };
}
function text6(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list4(spec, keys, fallback = []) {
  for (const key of keys) {
    const value = spec.content?.[key];
    if (Array.isArray(value)) {
      const cleaned = value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim());
      if (cleaned.length) return cleaned;
    }
  }
  return fallback;
}
function pill(theme, spec, label, index) {
  const dark = index % 2 === 0;
  return TextBlock(label.toLowerCase(), {
    height: 38,
    minWidth: Math.max(92, label.length * 17),
    padding: "4px 18px",
    borderRadius: 20,
    color: dark ? theme.yellow : theme.burgundy,
    backgroundColor: dark ? theme.burgundy : theme.yellow,
    ...fontRole("body", spec, { fontWeight: 900 }),
    fontSize: 21,
    lineHeight: 1.35
  });
}
function titleParts(title) {
  const cleaned = title || "Studio & Salon";
  if (cleaned.includes("&")) {
    const [left, right] = cleaned.split("&");
    return { left: left.trim() || "Studio", right: right.trim() || "Salon" };
  }
  const words = cleaned.split(/\s+/).filter(Boolean);
  const half = Math.max(1, Math.ceil(words.length / 2));
  return {
    left: words.slice(0, half).join(" ") || "Studio",
    right: words.slice(half).join(" ") || "Salon"
  };
}
function renderTritoneEditorialSpread(spec) {
  const theme = colors6(spec);
  const labels = list4(spec, ["points", "tags"], [
    "focus",
    "tech-equipped",
    "creativity",
    "coffee",
    "community",
    "coworking",
    "productivity",
    "inspiration",
    "flexible",
    "workshops",
    "collaboration",
    "studio"
  ]).slice(0, 12);
  const parts = titleParts(text6(spec, "title", "Studio & Salon"));
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.pink,
      color: theme.text,
      overflow: "hidden"
    },
    [
      TextBlock(text6(spec, "left_meta", "VOL. 04 \u2014 EDITORIAL BRIEF").toUpperCase(), {
        position: "absolute",
        left: 32,
        top: 34,
        color: theme.burgundy,
        ...fontRole("label", spec, { fontWeight: 800 }),
        fontSize: 13,
        letterSpacing: 5
      }),
      TextBlock(text6(spec, "center_meta", "SPRING / SUMMER EDITION").toUpperCase(), {
        position: "absolute",
        left: 344,
        top: 34,
        width: 280,
        color: theme.burgundy,
        textAlign: "center",
        ...fontRole("label", spec, { fontWeight: 800 }),
        fontSize: 13,
        letterSpacing: 5
      }),
      TextBlock(text6(spec, "right_meta", "FW \xB7 2026").toUpperCase(), {
        position: "absolute",
        right: 32,
        top: 34,
        width: 130,
        color: theme.burgundy,
        textAlign: "right",
        ...fontRole("metric", spec, { fontWeight: 800 }),
        fontSize: 13,
        letterSpacing: 5
      }),
      box(
        {
          position: "absolute",
          left: 32,
          top: 60,
          width: 760,
          flexDirection: "row",
          flexWrap: "wrap",
          gap: 11
        },
        labels.map((label, index) => pill(theme, spec, label, index))
      ),
      Title(parts.left, {
        position: "absolute",
        left: 32,
        bottom: 45,
        width: 420,
        color: theme.burgundy,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 98,
        lineHeight: 0.9
      }),
      Title("&", {
        position: "absolute",
        left: 446,
        bottom: 47,
        width: 86,
        color: theme.yellow,
        textAlign: "center",
        ...fontRole("display", spec, { fontWeight: 500 }),
        fontSize: 105,
        lineHeight: 0.85
      }),
      Title(parts.right, {
        position: "absolute",
        right: 28,
        bottom: 45,
        width: 410,
        color: theme.burgundy,
        textAlign: "right",
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 98,
        lineHeight: 0.9
      })
    ]
  );
}

// templates/beautiful/pixel-orbit-console.mjs
var templateId7 = "pixel-orbit-console";
var rendererContract7 = {
  template_id: templateId7,
  renderer_id: `artboard_satori.${templateId7}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "8-bit-orbit",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/8-bit-orbit-1.png"
};
function colors7(spec) {
  const source = spec.theme?.colors || {};
  return {
    void: source.background || "#0A0E27",
    navy: source.panel || "#0F1B3D",
    cyan: source.primary || "#5EDCF4",
    pink: source.accent || "#F0A6CA",
    yellow: source.yellow || "#F4D03F",
    lavender: source.muted || "#E2D5F2",
    grid: source.grid || "#1B2B55"
  };
}
function text7(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list5(spec, key, fallback = []) {
  const value = spec.content?.[key];
  if (!Array.isArray(value)) return fallback;
  const cleaned = value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim());
  return cleaned.length ? cleaned : fallback;
}
function grid(theme) {
  const vertical = Array.from({ length: 31 }).map(
    (_, index) => box({
      position: "absolute",
      left: index * 32,
      top: 0,
      width: 1,
      height: 540,
      backgroundColor: theme.grid,
      opacity: index % 5 === 0 ? 0.34 : 0.18
    })
  );
  const horizontal = Array.from({ length: 19 }).map(
    (_, index) => box({
      position: "absolute",
      left: 0,
      top: index * 30,
      width: 960,
      height: 1,
      backgroundColor: theme.grid,
      opacity: index % 4 === 0 ? 0.32 : 0.15
    })
  );
  return [...vertical, ...horizontal];
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
  ];
  return points.map(
    ([left, top, size, color]) => box({ position: "absolute", left, top, width: size, height: size, backgroundColor: color, opacity: 0.78 })
  );
}
function pixelTitle(value, top, theme, spec) {
  return [
    Title(value, {
      position: "absolute",
      left: 394,
      top: top + 7,
      width: 260,
      color: theme.navy,
      fontSize: 58,
      lineHeight: 0.88,
      textAlign: "center",
      ...fontRole("display", spec, { fontWeight: 900 })
    }),
    Title(value, {
      position: "absolute",
      left: 390,
      top: top + 5,
      width: 260,
      color: theme.yellow,
      fontSize: 58,
      lineHeight: 0.88,
      textAlign: "center",
      ...fontRole("display", spec, { fontWeight: 900 })
    }),
    Title(value, {
      position: "absolute",
      left: 384,
      top,
      width: 260,
      color: theme.cyan,
      fontSize: 58,
      lineHeight: 0.88,
      textAlign: "center",
      ...fontRole("display", spec, { fontWeight: 900 })
    })
  ];
}
function renderPixelOrbitConsole(spec) {
  const theme = colors7(spec);
  const title = text7(spec, "title", "8-BIT ORBIT").toUpperCase();
  const words = title.split(/\s+/);
  const lineOne = words.slice(0, Math.ceil(words.length / 2)).join(" ") || "8-BIT";
  const lineTwo = words.slice(Math.ceil(words.length / 2)).join(" ") || "ORBIT";
  const chips = list5(spec, "chips", ["10 SLIDES", "CSS NATIVE", "ZERO DEPENDENCIES"]).slice(0, 3);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.void,
      color: theme.lavender,
      overflow: "hidden"
    },
    [
      box({ position: "absolute", left: 0, top: 0, width: 960, height: 540, backgroundColor: theme.navy, opacity: 0.06 }),
      box({ position: "absolute", left: 0, top: 122, width: 318, height: 332, backgroundColor: "#0A1228", opacity: 0.52 }),
      box({ position: "absolute", left: 520, top: 0, width: 440, height: 540, backgroundColor: "#112144", opacity: 0.28 }),
      box({ position: "absolute", left: 0, top: 392, width: 960, height: 148, backgroundColor: "#080A25", opacity: 0.22 }),
      ...grid(theme),
      ...stars(theme),
      TextBlock(text7(spec, "eyebrow", "P I X E L   P E R F E C T   P R E S E N T A T I O N   S Y S T E M"), {
        position: "absolute",
        left: 218,
        top: 148,
        width: 540,
        color: theme.pink,
        fontSize: 8,
        lineHeight: 1,
        textAlign: "center",
        ...fontRole("label", spec, { fontWeight: 700 })
      }),
      ...pixelTitle(lineOne, 178, theme, spec),
      ...pixelTitle(lineTwo, 246, theme, spec),
      TextBlock(text7(spec, "subtitle", "A retro-futuristic deck engine for bold storytellers."), {
        position: "absolute",
        left: 348,
        top: 330,
        width: 300,
        color: theme.lavender,
        fontSize: 13,
        lineHeight: 1.7,
        textAlign: "center",
        ...fontRole("body", spec, { fontWeight: 500 })
      }),
      box(
        { position: "absolute", left: 374, top: 376, flexDirection: "row", gap: 8 },
        chips.map(
          (chip) => TextBlock(chip.toUpperCase(), {
            height: 18,
            minWidth: Math.max(52, chip.length * 8),
            borderWidth: 1,
            borderColor: theme.yellow,
            padding: "3px 10px",
            color: theme.yellow,
            fontSize: 7,
            lineHeight: 1,
            textAlign: "center",
            ...fontRole("label", spec, { fontWeight: 800 })
          })
        )
      ),
      box(
        { position: "absolute", right: 14, top: 214, flexDirection: "column", gap: 8 },
        Array.from({ length: 10 }).map(
          (_, index) => box({
            width: 7,
            height: 7,
            borderWidth: 1,
            borderColor: theme.cyan,
            backgroundColor: index === 0 ? theme.cyan : theme.void
          })
        )
      ),
      TextBlock(text7(spec, "page", "01 / 10"), {
        position: "absolute",
        left: 451,
        bottom: 17,
        width: 80,
        color: theme.cyan,
        fontSize: 8,
        lineHeight: 1,
        textAlign: "center",
        ...fontRole("metric", spec, { fontWeight: 700 })
      }),
      TextBlock(text7(spec, "hint", "USE KEYS + DOWN").toUpperCase(), {
        position: "absolute",
        right: 15,
        bottom: 15,
        width: 95,
        color: theme.cyan,
        fontSize: 6,
        lineHeight: 1,
        textAlign: "right",
        opacity: 0.72,
        ...fontRole("label", spec, { fontWeight: 700 })
      })
    ]
  );
}

// templates/beautiful/biennale-programme-poster.mjs
var templateId8 = "biennale-programme-poster";
var rendererContract8 = {
  template_id: templateId8,
  renderer_id: `artboard_satori.${templateId8}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "biennale-yellow",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/biennale-yellow-1.png"
};
function colors8(spec) {
  const source = spec.theme?.colors || {};
  return {
    paper: source.background || "#E9E5DB",
    paperDeep: source.panel || "#DCD6C4",
    sun: source.primary || "#F1EE2E",
    haze: source.accent || "#F0DA7C",
    ink: source.text || "#1B2566"
  };
}
function text8(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list6(spec, key, fallback = []) {
  const value = spec.content?.[key];
  if (!Array.isArray(value)) return fallback;
  const cleaned = value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim());
  return cleaned.length ? cleaned : fallback;
}
function footerColumn(theme, spec, { left, width, heading, body }) {
  return box(
    {
      position: "absolute",
      left,
      bottom: 18,
      width,
      flexDirection: "column",
      borderTopWidth: 1,
      borderTopColor: theme.ink,
      paddingTop: 8
    },
    [
      TextBlock(heading.toUpperCase(), {
        color: theme.ink,
        fontSize: 7,
        lineHeight: 1,
        marginBottom: 7,
        ...fontRole("label", spec, { fontWeight: 800 })
      }),
      TextBlock(body, {
        color: theme.ink,
        fontSize: 7,
        lineHeight: 1.45,
        ...fontRole("body", spec, { fontWeight: 400 })
      })
    ]
  );
}
function renderBiennaleProgrammePoster(spec) {
  const theme = colors8(spec);
  const title = text8(spec, "title", "Aurora Programme");
  const words = title.split(/\s+/);
  const first = words.slice(0, Math.max(1, Math.ceil(words.length / 2))).join(" ");
  const second = words.slice(Math.max(1, Math.ceil(words.length / 2))).join(" ") || "Programme";
  const notes = list6(spec, "notes", [
    "Aurora Institute for Public Form",
    "Fourth annual open programme",
    "A field study of light, matter and atmosphere.",
    "Six months of exhibitions across three pavilions."
  ]);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      box({ position: "absolute", left: 0, top: 135, width: 960, height: 405, backgroundColor: theme.sun, opacity: 0.9 }),
      box({ position: "absolute", right: 0, top: 0, width: 240, height: 132, backgroundColor: theme.haze, opacity: 0.62 }),
      box({ position: "absolute", left: 720, top: 204, width: 240, height: 136, backgroundColor: theme.paper, opacity: 0.92 }),
      box({ position: "absolute", left: 480, top: 338, width: 480, height: 135, backgroundColor: theme.paper, opacity: 0.72 }),
      TextBlock(text8(spec, "date", "02.05-\n11.10.2026"), {
        position: "absolute",
        right: 36,
        top: 20,
        width: 280,
        color: theme.ink,
        fontSize: 43,
        lineHeight: 0.82,
        textAlign: "right",
        whiteSpace: "pre-line",
        ...fontRole("metric", spec, { fontWeight: 400 })
      }),
      Title(first, {
        position: "absolute",
        left: 36,
        top: 166,
        width: 560,
        color: theme.ink,
        fontSize: 90,
        lineHeight: 0.85,
        ...fontRole("display", spec, { fontWeight: 400 })
      }),
      Title(second, {
        position: "absolute",
        left: 36,
        top: 250,
        width: 580,
        color: theme.ink,
        fontSize: 90,
        lineHeight: 0.85,
        ...fontRole("display", spec, { fontWeight: 400 })
      }),
      TextBlock(text8(spec, "eyebrow", "ANNUAL SURVEY \xB7 ISSUE NO. 04").toUpperCase(), {
        position: "absolute",
        left: 38,
        bottom: 76,
        color: theme.ink,
        fontSize: 8,
        lineHeight: 1,
        ...fontRole("label", spec, { fontWeight: 800 })
      }),
      footerColumn(theme, spec, { left: 38, width: 164, heading: "Hosted By", body: notes[0] || "Aurora Institute" }),
      footerColumn(theme, spec, { left: 224, width: 150, heading: "Edition", body: notes[1] || "Fourth annual programme" }),
      footerColumn(theme, spec, { left: 395, width: 208, heading: "Reading", body: notes[2] || "A field study of light." }),
      footerColumn(theme, spec, { left: 625, width: 296, heading: "Notes", body: notes[3] || "Six months of exhibitions and public lectures." }),
      TextBlock(text8(spec, "page", "01 / 08"), {
        position: "absolute",
        right: 24,
        bottom: 11,
        width: 58,
        color: theme.ink,
        fontSize: 8,
        textAlign: "right",
        ...fontRole("metric", spec, { fontWeight: 500 })
      })
    ]
  );
}

// templates/beautiful/block-frame-grid.mjs
var templateId9 = "block-frame-grid";
var rendererContract9 = {
  template_id: templateId9,
  renderer_id: `artboard_satori.${templateId9}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "block-frame",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/block-frame-1.png"
};
function colors9(spec) {
  const source = spec.theme?.colors || {};
  return {
    background: source.background || "#FFDC8B",
    paper: source.surface || "#FFFDF5",
    black: source.text || "#000000",
    pink: source.primary || "#FE90E8",
    green: source.accent || "#99E885",
    yellow: source.yellow || "#F7CB46",
    blue: source.blue || "#C0F7FE",
    white: "#FFFFFF"
  };
}
function text9(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function dotGrid(theme) {
  return Array.from({ length: 24 }).map(
    (_, index) => box({
      position: "absolute",
      left: 34 + index % 6 * 10,
      top: 35 + Math.floor(index / 6) * 10,
      width: 2,
      height: 2,
      borderRadius: 1,
      backgroundColor: theme.black,
      opacity: 0.55
    })
  );
}
function framedButton(theme, spec, label, style = {}) {
  return box(
    {
      width: 54,
      height: 24,
      backgroundColor: theme.white,
      borderWidth: 2,
      borderColor: theme.black,
      alignItems: "center",
      justifyContent: "center",
      ...style
    },
    [
      TextBlock(label, {
        color: theme.black,
        fontSize: 12,
        lineHeight: 1,
        textAlign: "center",
        ...fontRole("metric", spec, { fontWeight: 900 })
      })
    ]
  );
}
function shadowCard(theme, children) {
  return [
    box({ position: "absolute", left: 264, top: 147, width: 452, height: 274, backgroundColor: theme.black }),
    box(
      {
        position: "absolute",
        left: 256,
        top: 139,
        width: 452,
        height: 274,
        flexDirection: "column",
        backgroundColor: theme.paper,
        borderWidth: 3,
        borderColor: theme.black,
        padding: "30px 32px"
      },
      children
    )
  ];
}
function renderBlockFrameGrid(spec) {
  const theme = colors9(spec);
  const title = text9(spec, "title", "NEO-BRUTALISM STYLE").toUpperCase();
  const subtitle = text9(spec, "subtitle", "A bold, high-contrast template designed for maximum visual impact and uncompromising clarity.");
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.background,
      color: theme.black,
      overflow: "hidden"
    },
    [
      ...dotGrid(theme),
      ...shadowCard(theme, [
        TextBlock(text9(spec, "eyebrow", "PRESENTATION TEMPLATE").toUpperCase(), {
          width: 110,
          height: 20,
          borderWidth: 2,
          borderColor: theme.black,
          color: theme.black,
          fontSize: 8,
          lineHeight: 1,
          padding: "5px 7px",
          marginBottom: 16,
          ...fontRole("label", spec, { fontWeight: 900 })
        }),
        Title(title, {
          width: 330,
          color: theme.black,
          fontSize: 51,
          lineHeight: 0.92,
          marginBottom: 16,
          ...fontRole("display", spec, { fontWeight: 900 })
        }),
        TextBlock(subtitle, {
          width: 318,
          color: theme.black,
          fontSize: 11,
          lineHeight: 1.35,
          ...fontRole("body", spec, { fontWeight: 700 })
        })
      ]),
      box({ position: "absolute", left: 614, top: 118, width: 58, height: 52, backgroundColor: theme.black, transform: "rotate(12deg)" }),
      box({
        position: "absolute",
        left: 610,
        top: 112,
        width: 58,
        height: 52,
        backgroundColor: theme.pink,
        borderWidth: 2,
        borderColor: theme.black,
        transform: "rotate(12deg)"
      }),
      box({ position: "absolute", left: 616, top: 348, width: 32, height: 32, borderRadius: 16, backgroundColor: theme.green, borderWidth: 2, borderColor: theme.black }),
      box({ position: "absolute", left: 298, top: 401, width: 72, height: 20, backgroundColor: theme.black, transform: "rotate(-2deg)" }),
      box(
        {
          position: "absolute",
          left: 296,
          top: 397,
          width: 72,
          height: 20,
          backgroundColor: theme.yellow,
          borderWidth: 2,
          borderColor: theme.black,
          alignItems: "center",
          justifyContent: "center",
          transform: "rotate(-2deg)"
        },
        [
          TextBlock(text9(spec, "cta", "Get Started"), {
            color: theme.black,
            fontSize: 7,
            lineHeight: 1,
            ...fontRole("label", spec, { fontWeight: 900 })
          })
        ]
      ),
      framedButton(theme, spec, text9(spec, "page", "01 / 10"), { position: "absolute", left: 12, bottom: 10, width: 48 }),
      box(
        { position: "absolute", right: 12, bottom: 10, flexDirection: "row", gap: 8 },
        [
          framedButton(theme, spec, "<", { width: 24 }),
          framedButton(theme, spec, ">", { width: 24 })
        ]
      ),
      box({ position: "absolute", left: 462, top: 136, width: 10, height: 10, backgroundColor: theme.blue, borderWidth: 2, borderColor: theme.black })
    ]
  );
}

// templates/beautiful/broadside-editorial-quote.mjs
var templateId10 = "editorial-quote-chart";
var rendererContract10 = {
  template_id: templateId10,
  renderer_id: `artboard_satori.${templateId10}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "broadside",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/broadside-1.png"
};
function colors10(spec) {
  const source = spec.theme?.colors || {};
  return {
    orange: source.background || "#E85D26",
    black: source.text || "#111111",
    muted: source.muted || "#5E3526",
    cream: source.surface || "#F0ECE5"
  };
}
function text10(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function splitTitle(title) {
  const words = (title || "this is the broadside style").toLowerCase().split(/\s+/).filter(Boolean);
  return {
    first: words.slice(0, 4).join(" ") || "this is the",
    second: words.slice(4).join(" ") || "broadside style"
  };
}
function renderBroadsideEditorialQuote(spec) {
  const theme = colors10(spec);
  const parts = splitTitle(text10(spec, "title", "this is the broadside style"));
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.orange,
      color: theme.black,
      overflow: "hidden"
    },
    [
      TextBlock(text10(spec, "page", "01"), {
        position: "absolute",
        left: 54,
        top: 34,
        color: theme.muted,
        fontSize: 12,
        lineHeight: 1,
        ...fontRole("metric", spec, { fontWeight: 800 })
      }),
      TextBlock(text10(spec, "eyebrow", "BROADSIDE").toUpperCase(), {
        position: "absolute",
        right: 54,
        top: 34,
        width: 120,
        color: theme.muted,
        fontSize: 8,
        lineHeight: 1,
        textAlign: "right",
        ...fontRole("label", spec, { fontWeight: 700 })
      }),
      Title(parts.first, {
        position: "absolute",
        left: 54,
        top: 206,
        width: 820,
        color: theme.black,
        fontSize: 84,
        lineHeight: 0.78,
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      Title(parts.second, {
        position: "absolute",
        left: 54,
        top: 318,
        width: 860,
        color: theme.black,
        fontSize: 84,
        lineHeight: 0.78,
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      TextBlock(text10(spec, "subtitle", "Protest poster meets publication cover. Type so large it becomes image."), {
        position: "absolute",
        left: 54,
        bottom: 74,
        width: 420,
        color: theme.muted,
        fontSize: 15,
        lineHeight: 1.55,
        ...fontRole("body", spec, { fontWeight: 500 })
      }),
      box({ position: "absolute", left: 54, right: 54, bottom: 52, height: 1, backgroundColor: theme.muted, opacity: 0.45 }),
      TextBlock(text10(spec, "author", "[[Author Name]]"), {
        position: "absolute",
        left: 54,
        bottom: 27,
        color: theme.muted,
        fontSize: 11,
        ...fontRole("label", spec, { fontWeight: 700 })
      }),
      TextBlock(text10(spec, "context", "[Year] \xB7 Context"), {
        position: "absolute",
        right: 54,
        bottom: 27,
        width: 150,
        color: theme.muted,
        fontSize: 11,
        textAlign: "right",
        ...fontRole("label", spec, { fontWeight: 700 })
      })
    ]
  );
}

// templates/beautiful/cartesian-architectural-spec.mjs
var templateId11 = "architectural-spec";
var rendererContract11 = {
  template_id: templateId11,
  renderer_id: `artboard_satori.${templateId11}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "cartesian",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/cartesian-1.png"
};
function colors11(spec) {
  const source = spec.theme?.colors || {};
  return {
    paper: source.background || "#EDE8E0",
    ink: source.text || "#1A1A1A",
    muted: source.muted || "#5A5A5A",
    line: source.line || "#B8B0A4",
    accent: source.accent || "#8A8178"
  };
}
function text11(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function navButton(theme, spec, left, label) {
  return box(
    {
      position: "absolute",
      left,
      bottom: 22,
      width: 20,
      height: 20,
      borderWidth: 1,
      borderColor: theme.line,
      alignItems: "center",
      justifyContent: "center"
    },
    [
      TextBlock(label, {
        color: theme.ink,
        fontSize: 9,
        lineHeight: 1,
        textAlign: "center",
        ...fontRole("metric", spec, { fontWeight: 700 })
      })
    ]
  );
}
function renderCartesianArchitecturalSpec(spec) {
  const theme = colors11(spec);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      TextBlock(text11(spec, "eyebrow", "PRESENTATION TEMPLATE").toUpperCase(), {
        position: "absolute",
        left: 38,
        top: 214,
        color: theme.accent,
        fontSize: 7,
        lineHeight: 1,
        ...fontRole("label", spec, { fontWeight: 700 })
      }),
      Title(text11(spec, "title", "Cartesian"), {
        position: "absolute",
        left: 38,
        top: 246,
        width: 410,
        color: theme.ink,
        fontSize: 52,
        lineHeight: 1,
        ...fontRole("display", spec, { fontWeight: 400 })
      }),
      TextBlock(text11(spec, "subtitle", "A minimalist framework for strategic narratives. Clean geometry meets editorial refinement."), {
        position: "absolute",
        left: 38,
        top: 300,
        width: 380,
        color: theme.muted,
        fontSize: 12,
        lineHeight: 1.45,
        ...fontRole("body", spec, { fontWeight: 600 })
      }),
      box({ position: "absolute", right: 48, top: 198, width: 288, height: 288, borderRadius: 144, borderWidth: 1, borderColor: theme.line, opacity: 0.72 }),
      box({ position: "absolute", right: 76, top: 226, width: 232, height: 232, borderRadius: 116, borderWidth: 1, borderColor: theme.line, borderStyle: "dashed", opacity: 0.56 }),
      box(
        { position: "absolute", right: 20, top: 222, flexDirection: "column", gap: 6 },
        Array.from({ length: 10 }).map(
          (_, index) => box({ width: 4, height: 4, borderRadius: 2, backgroundColor: index === 0 ? theme.ink : theme.line })
        )
      ),
      navButton(theme, spec, 29, "<"),
      navButton(theme, spec, 57, ">"),
      TextBlock(text11(spec, "page", "01 / 10"), {
        position: "absolute",
        right: 30,
        bottom: 22,
        color: theme.accent,
        fontSize: 7,
        ...fontRole("metric", spec, { fontWeight: 500 })
      })
    ]
  );
}

// templates/beautiful/long-table-printed-program.mjs
var templateId12 = "printed-program";
var rendererContract12 = {
  template_id: templateId12,
  renderer_id: `artboard_satori.${templateId12}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "long-table",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/long-table-1.png"
};
function colors12(spec) {
  const source = spec.theme?.colors || {};
  return {
    paper: source.background || "#FAF1E2",
    ink: source.primary || "#B53D2A",
    deep: source.text || "#8E2D1F",
    soft: source.panel || "#F2E5CF"
  };
}
function text12(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function pill2(theme, spec, value, style = {}) {
  return TextBlock(value, {
    height: 22,
    minWidth: 64,
    borderWidth: 1,
    borderColor: theme.ink,
    borderRadius: 12,
    padding: "4px 15px",
    color: theme.ink,
    fontSize: 11,
    lineHeight: 1,
    textAlign: "center",
    ...fontRole("label", spec, { fontWeight: 600 }),
    ...style
  });
}
function renderLongTablePrintedProgram(spec) {
  const theme = colors12(spec);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      TextBlock(text12(spec, "edition", "5"), {
        position: "absolute",
        left: 49,
        top: 33,
        width: 22,
        height: 22,
        borderWidth: 1,
        borderColor: theme.ink,
        borderRadius: 11,
        color: theme.ink,
        fontSize: 11,
        lineHeight: 1,
        padding: "5px 0",
        textAlign: "center",
        ...fontRole("metric", spec, { fontWeight: 500 })
      }),
      TextBlock(text12(spec, "eyebrow", "december edition").toLowerCase(), {
        position: "absolute",
        left: 79,
        top: 38,
        color: theme.ink,
        fontSize: 16,
        lineHeight: 1,
        ...fontRole("body", spec, { fontWeight: 800 })
      }),
      Title(text12(spec, "title", "LONG\nTABLE").toUpperCase(), {
        position: "absolute",
        left: 48,
        top: 126,
        width: 300,
        color: theme.ink,
        fontSize: 74,
        lineHeight: 0.88,
        whiteSpace: "pre-line",
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      Title(text12(spec, "issue", "No.\n05"), {
        position: "absolute",
        right: 50,
        top: 70,
        width: 310,
        color: theme.ink,
        fontSize: 152,
        lineHeight: 0.86,
        textAlign: "right",
        whiteSpace: "pre-line",
        ...fontRole("display", spec, { fontWeight: 400 })
      }),
      box({ position: "absolute", left: 48, top: 337, flexDirection: "row", gap: 16 }, [
        pill2(theme, spec, text12(spec, "city", "Lisbon")),
        TextBlock("|", { color: theme.ink, fontSize: 16, lineHeight: 1.2, ...fontRole("body", spec) }),
        pill2(theme, spec, text12(spec, "cta", "Apply now"), { minWidth: 84 })
      ]),
      TextBlock(text12(spec, "availability", "22 seats only"), {
        position: "absolute",
        left: 48,
        top: 374,
        color: theme.ink,
        fontSize: 12,
        lineHeight: 1.2,
        ...fontRole("body", spec, { fontWeight: 900 })
      }),
      TextBlock(text12(spec, "lede", "More than dinner, it's a long evening."), {
        position: "absolute",
        left: 48,
        top: 394,
        width: 300,
        color: theme.ink,
        fontSize: 14,
        lineHeight: 1.35,
        ...fontRole("body", spec, { fontWeight: 600 })
      }),
      TextBlock(text12(spec, "badge", "Not a meal, an evening"), {
        position: "absolute",
        left: 48,
        top: 438,
        width: 160,
        height: 22,
        borderWidth: 1,
        borderColor: theme.ink,
        color: theme.ink,
        fontSize: 11,
        lineHeight: 1,
        padding: "5px 11px",
        ...fontRole("body", spec, { fontWeight: 600 })
      }),
      TextBlock(text12(spec, "right_meta", "DECEMBER \xB7 LISBON \xB7 EDITION").toUpperCase(), {
        position: "absolute",
        right: 48,
        top: 424,
        width: 250,
        color: theme.ink,
        fontSize: 9,
        lineHeight: 1,
        textAlign: "center",
        ...fontRole("label", spec, { fontWeight: 900 })
      }),
      TextBlock(text12(spec, "right_note", "Twice a month, ten strangers, one cook,\none long table. By application."), {
        position: "absolute",
        right: 48,
        top: 453,
        width: 250,
        color: theme.ink,
        fontSize: 12,
        lineHeight: 1.35,
        textAlign: "center",
        whiteSpace: "pre-line",
        ...fontRole("body", spec, { fontWeight: 600 })
      }),
      TextBlock(text12(spec, "page", "01 / 08"), {
        position: "absolute",
        right: 35,
        bottom: 13,
        color: theme.ink,
        fontSize: 8,
        ...fontRole("metric", spec, { fontWeight: 700 })
      })
    ]
  );
}

// templates/beautiful/monochrome-ledger-briefing.mjs
var templateId13 = "ledger-briefing";
var rendererContract13 = {
  template_id: templateId13,
  renderer_id: `artboard_satori.${templateId13}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "monochrome",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/monochrome-1.png"
};
function colors13(spec) {
  const source = spec.theme?.colors || {};
  return {
    paper: source.background || "#FAFADF",
    ink: source.text || "#1A1A16",
    muted: source.muted || "#5E5E54",
    line: source.line || "#1A1A16"
  };
}
function text13(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function titleLines(title) {
  const words = (title || "User Research Synthesis").split(/\s+/).filter(Boolean);
  return {
    first: words.slice(0, 2).join(" ") || "User Research",
    second: words.slice(2).join(" ") || "Synthesis"
  };
}
function renderMonochromeLedgerBriefing(spec) {
  const theme = colors13(spec);
  const title = titleLines(text13(spec, "title", "User Research Synthesis"));
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      TextBlock(text13(spec, "eyebrow", "USER RESEARCH SYNTHESIS / [MONTH, YEAR]").toUpperCase(), {
        position: "absolute",
        right: 109,
        top: 37,
        width: 260,
        color: theme.muted,
        fontSize: 7,
        lineHeight: 1,
        textAlign: "right",
        ...fontRole("label", spec, { fontWeight: 500 })
      }),
      Title(title.first, {
        position: "absolute",
        left: 110,
        top: 242,
        width: 520,
        color: theme.ink,
        fontSize: 60,
        lineHeight: 0.92,
        ...fontRole("display", spec, { fontWeight: 200 })
      }),
      Title(title.second, {
        position: "absolute",
        left: 110,
        top: 322,
        width: 520,
        color: theme.ink,
        fontSize: 60,
        lineHeight: 0.92,
        ...fontRole("display", spec, { fontWeight: 200 })
      }),
      box({ position: "absolute", left: 110, top: 415, width: 18, height: 1, backgroundColor: theme.ink }),
      TextBlock(text13(spec, "subtitle", "What we learned from 24 interviews and what it means for the product."), {
        position: "absolute",
        left: 110,
        bottom: 82,
        width: 620,
        color: theme.muted,
        fontSize: 14,
        lineHeight: 1.4,
        ...fontRole("body", spec, { fontWeight: 300 })
      }),
      box({ position: "absolute", left: 110, right: 78, bottom: 50, height: 1, backgroundColor: theme.ink }),
      TextBlock(text13(spec, "footer_left", "RESEARCH TEAM \xB7 [MONTH, YEAR]").toUpperCase(), {
        position: "absolute",
        left: 110,
        bottom: 34,
        color: theme.muted,
        fontSize: 7,
        ...fontRole("label", spec, { fontWeight: 500 })
      }),
      TextBlock(text13(spec, "footer_right", "ROUND [N] \xB7 INTERNAL").toUpperCase(), {
        position: "absolute",
        right: 110,
        bottom: 34,
        width: 170,
        color: theme.muted,
        fontSize: 7,
        textAlign: "right",
        ...fontRole("label", spec, { fontWeight: 500 })
      }),
      TextBlock(text13(spec, "page", "01 / 16"), {
        position: "absolute",
        right: 18,
        bottom: 9,
        color: theme.muted,
        fontSize: 6,
        ...fontRole("metric", spec, { fontWeight: 500 })
      })
    ]
  );
}

// templates/beautiful/capsule-card-system.mjs
var templateId14 = "capsule-card-system";
var rendererContract14 = {
  template_id: templateId14,
  renderer_id: `artboard_satori.${templateId14}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "capsule",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/capsule-1.png"
};
function colors14(spec) {
  const source = spec.theme?.colors || {};
  return {
    background: source.background || "#F4F4EE",
    ink: source.text || "#1A1A1A",
    muted: source.muted || "#77736D",
    yellow: source.panel || "#F2D160",
    coral: source.accent || "#E85D4E",
    lavender: source.lavender || "#CDB9E9",
    blue: source.blue || "#8DB7F2",
    lime: source.primary || "#C4D94E",
    peach: source.peach || "#F0B894"
  };
}
function text14(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function pill3(theme, spec, value, style = {}) {
  return box(
    {
      position: "absolute",
      minWidth: 84,
      height: 34,
      padding: "8px 18px",
      borderRadius: 999,
      borderWidth: 2,
      borderColor: theme.ink,
      backgroundColor: theme.yellow,
      alignItems: "center",
      justifyContent: "center",
      ...style
    },
    [
      TextBlock(value, {
        color: theme.ink,
        fontSize: 11,
        lineHeight: 1,
        textAlign: "center",
        ...fontRole("label", spec, { fontWeight: 900 })
      })
    ]
  );
}
function dotRail(theme) {
  return Array.from({ length: 10 }).map(
    (_, index) => box({
      position: "absolute",
      right: 34,
      top: 220 + index * 11,
      width: 6,
      height: 6,
      borderRadius: 3,
      borderWidth: index === 0 ? 0 : 1.5,
      borderColor: theme.ink,
      backgroundColor: index === 0 ? theme.ink : "transparent"
    })
  );
}
function renderCapsuleCardSystem(spec) {
  const theme = colors14(spec);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.background,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      box({ position: "absolute", left: 0, top: 0, width: 330, height: 540, backgroundColor: "#EEEEEA" }),
      box({ position: "absolute", right: 0, top: 0, width: 260, height: 540, backgroundColor: "#EEF2DE" }),
      box({ position: "absolute", left: 190, bottom: 0, width: 420, height: 190, backgroundColor: "#EFEFDF" }),
      pill3(theme, spec, text14(spec, "capsules", "Concept").split(",")[0] || "Concept", { left: 78, top: 67, backgroundColor: theme.coral, transform: "rotate(-12deg)" }),
      pill3(theme, spec, text14(spec, "stat", "2026"), { left: 432, top: 82, width: 44, height: 44, borderRadius: 22, backgroundColor: theme.peach, padding: "14px 0", transform: "rotate(0deg)" }),
      pill3(theme, spec, "Strategy", { right: 86, top: 100, backgroundColor: theme.lavender, transform: "rotate(8deg)" }),
      pill3(theme, spec, "Vision", { left: 144, bottom: 128, backgroundColor: theme.blue, transform: "rotate(7deg)" }),
      pill3(theme, spec, "Next", { left: 48, bottom: 90, width: 44, height: 44, borderRadius: 22, backgroundColor: "#9E67E8", padding: "16px 0" }),
      pill3(theme, spec, "Future", { right: 174, bottom: 80, backgroundColor: theme.lime, transform: "rotate(-9deg)" }),
      pill3(theme, spec, "Design", { right: 78, bottom: 152, backgroundColor: "transparent", borderColor: theme.muted, color: theme.muted, transform: "rotate(14deg)" }),
      ...dotRail(theme),
      pill3(theme, spec, text14(spec, "eyebrow", "Presentation Template"), {
        left: 402,
        top: 210,
        width: 156,
        height: 34,
        backgroundColor: theme.yellow,
        transform: "rotate(0deg)"
      }),
      Title(text14(spec, "title", "CAPSULE").toUpperCase(), {
        position: "absolute",
        left: 230,
        top: 264,
        width: 500,
        color: theme.ink,
        fontSize: 66,
        lineHeight: 1,
        textAlign: "center",
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      TextBlock(text14(spec, "subtitle", "A framework for bold ideas").toUpperCase(), {
        position: "absolute",
        left: 280,
        top: 330,
        width: 400,
        color: theme.muted,
        fontSize: 12,
        letterSpacing: 3,
        textAlign: "center",
        ...fontRole("body", spec, { fontWeight: 700 })
      }),
      TextBlock("USE ARROW KEYS TO NAVIGATE", {
        position: "absolute",
        left: 16,
        bottom: 16,
        color: "#B6B1AA",
        fontSize: 7,
        ...fontRole("label", spec, { fontWeight: 700 })
      }),
      TextBlock(text14(spec, "page", "01 / 10"), {
        position: "absolute",
        right: 16,
        bottom: 16,
        color: theme.muted,
        fontSize: 8,
        ...fontRole("metric", spec, { fontWeight: 700 })
      })
    ]
  );
}

// templates/beautiful/creative-mode-grid.mjs
var templateId15 = "creative-mode-grid";
var rendererContract15 = {
  template_id: templateId15,
  renderer_id: `artboard_satori.${templateId15}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "creative-mode",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/creative-mode-1.png"
};
function colors15(spec) {
  const source = spec.theme?.colors || {};
  return {
    paper: source.background || "#EFE9D9",
    ink: source.text || "#101010",
    green: source.primary || "#1F8A4C",
    orange: source.accent || "#E85A1F",
    pink: source.pink || "#E966A6",
    blush: source.panel || "#F2C7D8"
  };
}
function text15(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function titleLines2(value) {
  const words = value.toUpperCase().split(/\s+/).filter(Boolean);
  return {
    first: words.slice(0, 2).join(" ") || "CREATIVE",
    second: words.slice(2).join(" ") || "MODE"
  };
}
function renderCreativeModeGrid(spec) {
  const theme = colors15(spec);
  const title = titleLines2(text15(spec, "title", "CREATIVE MODE"));
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      box({ position: "absolute", left: 48, top: 86, width: 30, height: 2, backgroundColor: theme.ink }),
      TextBlock("VOL. 01 / EDITION 2026", {
        position: "absolute",
        left: 88,
        top: 82,
        color: theme.ink,
        fontSize: 14,
        letterSpacing: 6,
        ...fontRole("metric", spec, { fontWeight: 800 })
      }),
      Title(title.first, {
        position: "absolute",
        left: 48,
        top: 200,
        width: 470,
        color: theme.ink,
        fontSize: 78,
        lineHeight: 0.9,
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      Title(title.second, {
        position: "absolute",
        left: 48,
        top: 274,
        width: 370,
        color: theme.orange,
        fontSize: 78,
        lineHeight: 0.9,
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      TextBlock(text15(spec, "subtitle", "A presentation template - eight pages, eight layouts. Replace freely."), {
        position: "absolute",
        left: 48,
        top: 438,
        width: 430,
        color: "#2C2922",
        fontSize: 15,
        lineHeight: 1.35,
        ...fontRole("body", spec, { fontWeight: 500 })
      }),
      TextBlock(text15(spec, "eyebrow", "A PRESENTATION TEMPLATE").toUpperCase(), {
        position: "absolute",
        left: 32,
        bottom: 20,
        color: theme.ink,
        fontSize: 12,
        letterSpacing: 5,
        ...fontRole("label", spec, { fontWeight: 800 })
      }),
      box({ position: "absolute", right: 48, top: 70, width: 384, height: 400, backgroundColor: theme.green, borderWidth: 2, borderColor: theme.ink }),
      box({ position: "absolute", right: 82, top: 184, width: 198, height: 198, backgroundColor: theme.orange, borderWidth: 2, borderColor: theme.ink }),
      box({ position: "absolute", right: 96, top: 174, width: 194, height: 194, backgroundColor: theme.pink, borderWidth: 2, borderColor: theme.ink }),
      box({ position: "absolute", right: 132, top: 216, width: 124, height: 86, backgroundColor: theme.blush, borderWidth: 2, borderColor: theme.ink, transform: "rotate(-7deg)" }),
      box({ position: "absolute", right: 134, top: 294, width: 120, height: 17, backgroundColor: "#D24784", transform: "rotate(-7deg)" }),
      TextBlock("01 * 08", {
        position: "absolute",
        right: 32,
        bottom: 18,
        color: theme.ink,
        fontSize: 13,
        letterSpacing: 4,
        ...fontRole("metric", spec, { fontWeight: 900 })
      })
    ]
  );
}

// templates/beautiful/daisy-workshop-playbook.mjs
var templateId16 = "daisy-workshop-playbook";
var rendererContract16 = {
  template_id: templateId16,
  renderer_id: `artboard_satori.${templateId16}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "daisy-days",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/daisy-days-1.png"
};
function colors16(spec) {
  const source = spec.theme?.colors || {};
  return {
    cream: source.background || "#F5F0E6",
    ink: source.text || "#2D2D2D",
    muted: source.muted || "#696765",
    yellow: source.panel || "#FDE68A",
    pink: source.primary || "#F7C8D4",
    mint: source.accent || "#7ECDC0",
    white: source.surface || "#FFFFFF"
  };
}
function text16(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function flower(theme, left, top, scale = 1) {
  const size = 112 * scale;
  const petalWidth = 44 * scale;
  const petalHeight = 76 * scale;
  return box(
    { position: "absolute", left, top, width: size, height: size },
    [
      ...[0, 45, 90, 135, 180, 225, 270, 315].map(
        (rotation, index) => box({
          position: "absolute",
          left: 34 * scale + Math.cos(rotation * Math.PI / 180) * 26 * scale,
          top: 18 * scale + Math.sin(rotation * Math.PI / 180) * 26 * scale,
          width: petalWidth,
          height: petalHeight,
          borderRadius: 24 * scale,
          borderWidth: 2,
          borderColor: theme.ink,
          backgroundColor: theme.white,
          transform: `rotate(${rotation}deg)`,
          opacity: index % 2 === 0 ? 1 : 0.96
        })
      ),
      box({
        position: "absolute",
        left: 42 * scale,
        top: 42 * scale,
        width: 34 * scale,
        height: 34 * scale,
        borderRadius: 17 * scale,
        borderWidth: 2,
        borderColor: theme.ink,
        backgroundColor: theme.yellow
      })
    ]
  );
}
function star(theme, left, top, color) {
  return box({
    position: "absolute",
    left,
    top,
    width: 36,
    height: 36,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: theme.ink,
    backgroundColor: color,
    transform: "rotate(35deg)"
  });
}
function dotRail2(theme) {
  return Array.from({ length: 10 }).map(
    (_, index) => box({
      position: "absolute",
      right: 12,
      top: 218 + index * 11,
      width: 6,
      height: 6,
      borderRadius: 3,
      borderWidth: 1.5,
      borderColor: theme.ink,
      backgroundColor: index === 0 ? theme.yellow : "transparent"
    })
  );
}
function renderDaisyWorkshopPlaybook(spec) {
  const theme = colors16(spec);
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.cream,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      flower(theme, -24, -10, 0.82),
      flower(theme, 878, 14, 0.56),
      flower(theme, 22, 462, 0.7),
      flower(theme, 874, 432, 0.82),
      star(theme, 68, 72, theme.pink),
      star(theme, 846, 100, theme.mint),
      star(theme, 104, 408, theme.yellow),
      ...dotRail2(theme),
      TextBlock(text16(spec, "eyebrow", "Workshop Playbook").toUpperCase(), {
        position: "absolute",
        left: 340,
        top: 198,
        width: 280,
        color: theme.ink,
        textAlign: "center",
        ...fontRole("label", spec, { fontWeight: 900 }),
        fontSize: 11,
        lineHeight: 1
      }),
      Title(text16(spec, "title", "Daisy Days"), {
        position: "absolute",
        left: 200,
        top: 230,
        width: 520,
        color: theme.ink,
        textAlign: "center",
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 76,
        lineHeight: 1
      }),
      TextBlock(text16(spec, "subtitle", "A cheerful presentation template for bright moments"), {
        position: "absolute",
        left: 220,
        top: 314,
        width: 520,
        color: theme.ink,
        textAlign: "center",
        ...fontRole("body", spec, { fontWeight: 900 }),
        fontSize: 20,
        lineHeight: 1.25
      }),
      box({
        position: "absolute",
        left: 420,
        top: 354,
        width: 120,
        height: 2,
        borderRadius: 1,
        backgroundColor: theme.ink
      }),
      box(
        {
          position: "absolute",
          left: 390,
          bottom: 8,
          width: 180,
          height: 28,
          borderRadius: 10,
          backgroundColor: theme.ink
        }
      ),
      box(
        {
          position: "absolute",
          left: 410,
          bottom: 18,
          width: 140,
          height: 18,
          borderRadius: 10,
          borderWidth: 2,
          borderColor: theme.ink,
          backgroundColor: theme.white,
          alignItems: "center",
          justifyContent: "center"
        },
        [
          TextBlock(text16(spec, "page", "1 / 10"), {
            color: theme.ink,
            ...fontRole("metric", spec, { fontWeight: 900 }),
            fontSize: 8,
            lineHeight: 1
          })
        ]
      )
    ]
  );
}

// templates/beautiful/emerald-editorial-cover.mjs
var templateId17 = "emerald-editorial-cover";
var rendererContract17 = {
  template_id: templateId17,
  renderer_id: `artboard_satori.${templateId17}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "emerald-editorial",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/emerald-editorial-1.png"
};
function colors17(spec) {
  const source = spec.theme?.colors || {};
  return {
    emerald: source.background || "#3CD896",
    navy: source.text || "#0F1A5C",
    paper: source.panel || "#F1E9D6"
  };
}
function text17(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function coverWords(title) {
  const words = title.toUpperCase().split(/\s+/).filter(Boolean);
  if (words.length >= 4) {
    return {
      top: words.slice(0, 2).join(" "),
      bottom: words.slice(2).join(" ")
    };
  }
  return { top: "STATE", bottom: "THE WORK AHEAD" };
}
function renderEmeraldEditorialCover(spec) {
  const theme = colors17(spec);
  const words = coverWords(text17(spec, "title", "The State of the Work Ahead"));
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.emerald,
      color: theme.navy,
      overflow: "hidden"
    },
    [
      TextBlock("The", {
        position: "absolute",
        left: 440,
        top: 79,
        width: 88,
        color: theme.navy,
        fontSize: 42,
        lineHeight: 0.9,
        textAlign: "center",
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      Title(words.top, {
        position: "absolute",
        left: 260,
        top: 120,
        width: 440,
        color: theme.navy,
        fontSize: 86,
        lineHeight: 0.9,
        textAlign: "center",
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      box({ position: "absolute", left: 130, top: 216, width: 314, height: 3, backgroundColor: theme.navy }),
      box({ position: "absolute", left: 130, top: 223, width: 314, height: 3, backgroundColor: theme.navy }),
      TextBlock("of", {
        position: "absolute",
        left: 454,
        top: 208,
        width: 52,
        color: theme.navy,
        fontSize: 40,
        lineHeight: 1,
        textAlign: "center",
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      box({ position: "absolute", right: 130, top: 216, width: 314, height: 3, backgroundColor: theme.navy }),
      box({ position: "absolute", right: 130, top: 223, width: 314, height: 3, backgroundColor: theme.navy }),
      Title(words.bottom, {
        position: "absolute",
        left: 200,
        top: 246,
        width: 560,
        color: theme.navy,
        fontSize: 70,
        lineHeight: 0.92,
        textAlign: "center",
        ...fontRole("display", spec, { fontWeight: 900 })
      }),
      TextBlock(text17(spec, "subtitle", "A presentation for the leadership team").toUpperCase(), {
        position: "absolute",
        left: 280,
        top: 430,
        width: 400,
        color: theme.navy,
        fontSize: 14,
        letterSpacing: 5,
        textAlign: "center",
        ...fontRole("body", spec, { fontWeight: 900 })
      }),
      TextBlock("PREPARED BY THE PLANNING OFFICE", {
        position: "absolute",
        left: 56,
        bottom: 32,
        color: theme.navy,
        fontSize: 14,
        ...fontRole("label", spec, { fontWeight: 900 })
      }),
      TextBlock("NOVEMBER \xB7 MMXXV", {
        position: "absolute",
        right: 56,
        bottom: 32,
        color: theme.navy,
        fontSize: 14,
        textAlign: "right",
        ...fontRole("metric", spec, { fontWeight: 900 })
      })
    ]
  );
}

// templates/beautiful/trend-grid-report.mjs
var templateId18 = "trend-grid-report";
var rendererContract18 = {
  template_id: templateId18,
  renderer_id: `artboard_satori.${templateId18}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "cobalt-grid",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/cobalt-grid-1.png"
};
function colors18(spec) {
  const source = spec.theme?.colors || {};
  return {
    paper: source.background || "#F0EBDE",
    cobalt: source.primary || "#1F2BE0",
    soft: source.muted || "#5560E5"
  };
}
function text18(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function graphGrid(theme) {
  const lines = [];
  for (let x = 34; x < 930; x += 24) {
    lines.push(box({ position: "absolute", left: x, top: 14, width: 1, height: 512, backgroundColor: theme.cobalt, opacity: 0.08 }));
  }
  for (let y = 14; y < 528; y += 24) {
    lines.push(box({ position: "absolute", left: 34, top: y, width: 892, height: 1, backgroundColor: theme.cobalt, opacity: 0.08 }));
  }
  return lines;
}
function glitch(theme) {
  const segments = [];
  const slices = [
    { left: 742, top: 34, height: 58, bars: 10 },
    { left: 792, top: 84, height: 92, bars: 8 },
    { left: 704, top: 168, height: 146, bars: 12 },
    { left: 760, top: 306, height: 70, bars: 8 },
    { left: 720, top: 368, height: 122, bars: 12 },
    { left: 798, top: 482, height: 62, bars: 8 }
  ];
  slices.forEach(({ left, top, height, bars }) => {
    for (let i = 0; i < bars; i += 1) {
      segments.push(box({ position: "absolute", left: left + i * 6, top, width: 3, height, backgroundColor: theme.cobalt }));
    }
  });
  return segments;
}
function renderTrendGridReport(spec) {
  const theme = colors18(spec);
  const titleParts2 = text18(spec, "title", "Index\n2026").split(/\n+/);
  return box(
    { width: 960, height: 540, position: "relative", backgroundColor: theme.paper, color: theme.cobalt, overflow: "hidden" },
    [
      ...graphGrid(theme),
      box({ position: "absolute", left: 34, top: 14, width: 892, height: 1, backgroundColor: theme.cobalt }),
      box({ position: "absolute", left: 34, bottom: 14, width: 892, height: 1, backgroundColor: theme.cobalt }),
      Title(titleParts2[0] || "Index", {
        position: "absolute",
        left: 38,
        top: 112,
        width: 320,
        color: theme.cobalt,
        ...fontRole("display", spec, { fontWeight: 400 }),
        fontSize: 82,
        lineHeight: 1,
        textTransform: "none"
      }),
      Title(titleParts2[1] || "2026", {
        position: "absolute",
        left: 38,
        top: 220,
        width: 320,
        color: theme.cobalt,
        ...fontRole("display", spec, { fontWeight: 400 }),
        fontSize: 82,
        lineHeight: 1,
        textTransform: "none"
      }),
      TextBlock(text18(spec, "eyebrow", "FIELD OFFICE QUARTERLY \xB7 VOLUME IV").toUpperCase(), {
        position: "absolute",
        left: 34,
        top: 356,
        width: 340,
        color: theme.cobalt,
        ...fontRole("label", spec, { fontWeight: 900 }),
        fontSize: 9,
        lineHeight: 1
      }),
      TextBlock(text18(spec, "subtitle", "A field report on the state of things."), {
        position: "absolute",
        left: 34,
        top: 384,
        width: 470,
        color: theme.cobalt,
        ...fontRole("display", spec, { fontWeight: 400 }),
        fontSize: 18,
        lineHeight: 1.08,
        textTransform: "none"
      }),
      ...glitch(theme),
      TextBlock(text18(spec, "vertical", "issue.04  spring 2026  field-office.co"), {
        position: "absolute",
        right: 26,
        top: 184,
        width: 12,
        color: theme.cobalt,
        ...fontRole("metric", spec, { fontWeight: 800 }),
        fontSize: 8,
        lineHeight: 1.2
      }),
      TextBlock(text18(spec, "footer_left", "EDITED BY\nField Office Editorial \xB7 Lin Ito & Anya Mehrotra"), {
        position: "absolute",
        left: 34,
        bottom: 46,
        width: 260,
        color: theme.cobalt,
        ...fontRole("metric", spec, { fontWeight: 700 }),
        fontSize: 8,
        whiteSpace: "pre-wrap",
        lineHeight: 1.5
      }),
      TextBlock(text18(spec, "footer_right", "DISTRIBUTED\nTo subscribers & the open web \xB7 twice a year"), {
        position: "absolute",
        left: 216,
        bottom: 46,
        width: 300,
        color: theme.cobalt,
        ...fontRole("body", spec, { fontWeight: 700 }),
        fontSize: 8,
        whiteSpace: "pre-wrap",
        lineHeight: 1.5
      }),
      TextBlock(text18(spec, "page", "01 / 08"), {
        position: "absolute",
        right: 34,
        bottom: 30,
        color: theme.cobalt,
        ...fontRole("metric", spec, { fontWeight: 800 }),
        fontSize: 8
      })
    ]
  );
}

// templates/beautiful/product-ribbon.mjs
var templateId19 = "product-ribbon";
var rendererContract19 = {
  template_id: templateId19,
  renderer_id: `artboard_satori.${templateId19}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "sakura-chroma",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/sakura-chroma-1.png"
};
function colors19(spec) {
  const source = spec.theme?.colors || {};
  return {
    paper: source.background || "#F1E6CB",
    ink: source.text || "#3A2516",
    red: source.red || "#E5392A",
    pink: source.primary || "#E54489",
    orange: source.orange || "#F09131",
    green: source.green || "#3D9F47",
    blue: source.blue || "#3F8BC4",
    yellow: source.panel || "#F0BC2A"
  };
}
function text19(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function petalCluster(theme) {
  const colors36 = [theme.red, theme.blue, theme.green, theme.orange, theme.yellow];
  return box(
    { position: "absolute", left: 34, top: 20, width: 205, height: 154 },
    colors36.map(
      (color, index) => box({
        position: "absolute",
        left: [0, 54, 100, 28, 70][index],
        top: [44, 0, 38, 82, 82][index],
        width: [96, 84, 96, 74, 62][index],
        height: [94, 84, 96, 74, 62][index],
        borderRadius: 999,
        backgroundColor: color
      })
    )
  );
}
function ribbon(theme, top, color, width, offset, height = 58) {
  return box({
    position: "absolute",
    left: 460 + offset,
    top,
    width,
    height,
    backgroundColor: color,
    transform: "skewY(-12deg)"
  });
}
function checkbox(theme, label, top, checked) {
  return box(
    { position: "absolute", right: 78, top, width: 110, height: 18, flexDirection: "row", alignItems: "center" },
    [
      box({
        width: 10,
        height: 10,
        borderWidth: 1.5,
        borderColor: theme.ink,
        backgroundColor: checked ? theme.ink : "transparent",
        marginRight: 8
      }),
      TextBlock(label.toUpperCase(), {
        color: theme.ink,
        ...fontRole("label", null, { fontWeight: 900 }),
        fontSize: 11,
        lineHeight: 1
      })
    ]
  );
}
function renderProductRibbon(spec) {
  const theme = colors19(spec);
  const title = text19(spec, "title", "T-26");
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.paper,
      color: theme.ink,
      overflow: "hidden"
    },
    [
      petalCluster(theme),
      TextBlock(text19(spec, "brand", "tape\ngarden").toLowerCase(), {
        position: "absolute",
        left: 230,
        top: 48,
        width: 120,
        color: theme.ink,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 30,
        lineHeight: 0.82,
        whiteSpace: "pre-wrap"
      }),
      TextBlock(text19(spec, "edition", "CATALOGUE NO. 7").toUpperCase(), {
        position: "absolute",
        left: 231,
        top: 104,
        width: 170,
        color: theme.ink,
        ...fontRole("label", spec, { fontWeight: 900 }),
        fontSize: 10
      }),
      Title(title, {
        position: "absolute",
        left: 34,
        top: 160,
        width: 250,
        color: theme.ink,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 106,
        lineHeight: 0.86
      }),
      ribbon(theme, 90, theme.pink, 560, 0),
      ribbon(theme, 110, theme.orange, 560, -20),
      ribbon(theme, 132, theme.yellow, 650, -8),
      ribbon(theme, 154, theme.green, 650, 2),
      ribbon(theme, 176, theme.blue, 700, -12),
      checkbox(theme, "Color", 174, true),
      checkbox(theme, "Lo-Fi", 218, true),
      checkbox(theme, "Stereo", 262, false),
      checkbox(theme, "LP", 306, false),
      TextBlock(text19(spec, "subtitle", "SUPERCATALOG").toUpperCase(), {
        position: "absolute",
        left: 34,
        bottom: 86,
        width: 364,
        backgroundColor: theme.pink,
        color: theme.paper,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 40,
        lineHeight: 1,
        padding: "6px 16px 8px"
      }),
      box({ position: "absolute", left: 34, right: 34, bottom: 78, height: 1, backgroundColor: theme.ink }),
      TextBlock(text19(spec, "footer_left", "\u9650\u5B9A\u7248  made in matsumoto     N.R. :  \u25A0 ON   \u25A1 OFF"), {
        position: "absolute",
        left: 34,
        bottom: 36,
        width: 360,
        color: theme.ink,
        ...fontRole("body", spec, { fontWeight: 800 }),
        fontSize: 8
      }),
      box({ position: "absolute", right: 106, bottom: 24, width: 60, height: 26, backgroundColor: theme.red, alignItems: "center", justifyContent: "center" }, [
        TextBlock(text19(spec, "stamp", "AS SEEN ON\nTG").toUpperCase(), {
          color: theme.paper,
          ...fontRole("label", spec, { fontWeight: 900 }),
          fontSize: 7,
          lineHeight: 1.1,
          textAlign: "center",
          whiteSpace: "pre-wrap"
        })
      ]),
      TextBlock(text19(spec, "page", "01 / 08"), {
        position: "absolute",
        right: 20,
        bottom: 12,
        width: 70,
        color: theme.ink,
        textAlign: "right",
        ...fontRole("metric", spec, { fontWeight: 900 }),
        fontSize: 7
      })
    ]
  );
}

// templates/beautiful/brutalist-matrix.mjs
var templateId20 = "brutalist-matrix";
var rendererContract20 = {
  template_id: templateId20,
  renderer_id: `artboard_satori.${templateId20}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "raw-grid",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/raw-grid-1.png"
};
function colors20(spec) {
  const source = spec.theme?.colors || {};
  return {
    black: source.text || "#0A0A0A",
    white: source.surface || "#FFFFFF",
    pink: source.primary || "#F2D4CF",
    green: source.accent || "#E5EDD6"
  };
}
function text20(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list7(spec, keys, fallback = []) {
  for (const key of keys) {
    const value = spec.content?.[key];
    if (Array.isArray(value)) {
      const cleaned = value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim());
      if (cleaned.length) return cleaned;
    }
  }
  return fallback;
}
function row(theme, spec, label, index) {
  return box(
    {
      position: "absolute",
      left: 480,
      top: index * 77,
      width: 480,
      height: 78,
      backgroundColor: index === 2 ? theme.green : theme.white,
      borderBottomWidth: 2,
      borderBottomColor: theme.black,
      flexDirection: "row",
      alignItems: "center",
      paddingLeft: 44
    },
    [
      TextBlock("\u2192", { color: theme.black, width: 28, ...fontRole("metric", null, { fontWeight: 900 }), fontSize: 22 }),
      TextBlock(label.toUpperCase(), {
        color: theme.black,
        ...fontRole("body", spec, { fontWeight: 900 }),
        fontSize: 15,
        lineHeight: 1
      })
    ]
  );
}
function renderBrutalistMatrix(spec) {
  const theme = colors20(spec);
  const rows = list7(spec, ["cities", "cells", "items"], ["San Francisco", "New York", "Cupertino", "Menlo Park", "Santa Clara", "Mountain View", "Sunnyvale"]).slice(0, 7);
  return box(
    { width: 960, height: 540, position: "relative", backgroundColor: theme.white, color: theme.black, overflow: "hidden" },
    [
      box({ position: "absolute", left: 0, top: 0, width: 480, height: 540, backgroundColor: theme.pink }),
      box({ position: "absolute", left: 32, top: 34, width: 24, height: 24, borderWidth: 2, borderColor: theme.black, alignItems: "center", justifyContent: "center" }, [
        TextBlock(text20(spec, "mark", "RG"), { color: theme.black, ...fontRole("label", spec, { fontWeight: 900 }), fontSize: 10 })
      ]),
      TextBlock(text20(spec, "eyebrow", "RAW GRID").toUpperCase(), {
        position: "absolute",
        left: 62,
        top: 42,
        width: 140,
        color: theme.black,
        ...fontRole("label", spec, { fontWeight: 900 }),
        fontSize: 10
      }),
      Title(text20(spec, "title", "CITIES.\nSTARTUPS.").toUpperCase(), {
        position: "absolute",
        left: 32,
        top: 232,
        width: 390,
        color: theme.black,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: 48,
        lineHeight: 0.94,
        whiteSpace: "pre-wrap"
      }),
      TextBlock(text20(spec, "callout", "\u2192 DISCOVER ALL STARTUPS").toUpperCase(), {
        position: "absolute",
        left: 32,
        bottom: 32,
        width: 160,
        color: theme.white,
        backgroundColor: theme.black,
        ...fontRole("label", spec, { fontWeight: 900 }),
        fontSize: 7,
        lineHeight: 1,
        padding: "5px 8px"
      }),
      ...rows.map((item, index) => row(theme, spec, item, index))
    ]
  );
}

// templates/beautiful/type-mass-poster.mjs
var templateId21 = "type-mass-poster";
var rendererContract21 = {
  template_id: templateId21,
  renderer_id: `artboard_satori.${templateId21}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "studio",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/studio-1.png"
};
function colors21(spec) {
  const source = spec.theme?.colors || {};
  return {
    black: source.background || "#1C1C1C",
    yellow: source.primary || "#F5D200",
    muted: source.muted || "#9A860C"
  };
}
function text21(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function renderTypeMassPoster(spec) {
  const theme = colors21(spec);
  const title = text21(spec, "title", "PROPOSAL").toUpperCase();
  return box(
    {
      width: 960,
      height: 540,
      position: "relative",
      backgroundColor: theme.black,
      color: theme.yellow,
      overflow: "hidden"
    },
    [
      Title(title, {
        position: "absolute",
        left: 52,
        top: 42,
        width: 720,
        color: theme.yellow,
        ...fontRole("display", spec, { fontWeight: 900 }),
        fontSize: title.length <= 9 ? 112 : 86,
        lineHeight: 0.88
      }),
      TextBlock(text21(spec, "image_label", "IMAGE PLACEHOLDER").toUpperCase(), {
        position: "absolute",
        left: 438,
        top: 267,
        width: 210,
        color: theme.muted,
        ...fontRole("label", spec, { fontWeight: 800 }),
        fontSize: 9,
        lineHeight: 1
      }),
      box({ position: "absolute", left: 0, bottom: 64, width: 960, height: 1, backgroundColor: theme.yellow, opacity: 0.45 }),
      TextBlock(text21(spec, "footer_left", "[Studio Name] \xD7 [Client Name]\n[Date]"), {
        position: "absolute",
        left: 50,
        bottom: 26,
        width: 260,
        color: theme.yellow,
        ...fontRole("metric", spec, { fontWeight: 800 }),
        fontSize: 10,
        lineHeight: 1.55,
        whiteSpace: "pre-wrap"
      }),
      TextBlock(text21(spec, "footer_center", "[Presentation Title]"), {
        position: "absolute",
        left: 382,
        bottom: 42,
        width: 210,
        color: theme.yellow,
        textAlign: "center",
        ...fontRole("body", spec, { fontWeight: 800 }),
        fontSize: 10,
        lineHeight: 1
      }),
      TextBlock(text21(spec, "footer_right", "[Studio Name]"), {
        position: "absolute",
        right: 50,
        bottom: 42,
        width: 190,
        color: theme.yellow,
        textAlign: "right",
        ...fontRole("metric", spec, { fontWeight: 800 }),
        fontSize: 10,
        lineHeight: 1
      }),
      TextBlock(text21(spec, "page", "1 / 12"), {
        position: "absolute",
        right: 22,
        bottom: 10,
        width: 60,
        color: theme.muted,
        textAlign: "right",
        ...fontRole("metric", spec, { fontWeight: 800 }),
        fontSize: 7
      })
    ]
  );
}

// templates/beautiful/serif-stat-editorial.mjs
var templateId22 = "serif-stat-editorial";
var rendererContract22 = {
  template_id: templateId22,
  renderer_id: `artboard_satori.${templateId22}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "editorial-forest",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/editorial-forest-1.png"
};
function colors22(spec) {
  return {
    background: "#244A2E",
    text: "#ECA0B5",
    muted: "#E7D8BE",
    line: "#ECA0B5"
  };
}
function text22(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list8(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderSerifStatEditorial(spec) {
  const theme = colors22(spec);
  const cards = list8(spec, "cards", ["Studio placeholder", "Presented by name", "Review note"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.background, overflow: "hidden" }, [
    TextBlock(text22(spec, "eyebrow", "A PRESENTATION TEMPLATE").toUpperCase(), {
      position: "absolute",
      left: 66,
      top: 39,
      color: theme.muted,
      fontSize: 7,
      letterSpacing: 1.4,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    box({
      position: "absolute",
      right: 96,
      top: 34,
      width: 34,
      height: 34,
      borderRadius: 999,
      borderWidth: 1,
      borderColor: theme.line,
      alignItems: "center",
      justifyContent: "center"
    }, [
      TextBlock("01", { color: theme.muted, fontSize: 7, ...fontRole("metric", spec, { fontWeight: 400 }) })
    ]),
    Title(text22(spec, "title", "Quarterly\nReview\n2026"), {
      position: "absolute",
      left: 70,
      top: 116,
      width: 386,
      color: theme.text,
      fontSize: 64,
      lineHeight: 0.92,
      whiteSpace: "pre-line",
      ...fontRole("display", spec, { fontWeight: 400, letterSpacing: -0.5 })
    }),
    TextBlock(text22(spec, "subtitle", cards[0] || "Studio placeholder").toUpperCase(), {
      position: "absolute",
      left: 70,
      bottom: 72,
      color: theme.text,
      fontSize: 8,
      letterSpacing: 1.2,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    TextBlock((cards[1] || "Presented by name").toUpperCase(), {
      position: "absolute",
      right: 86,
      bottom: 72,
      color: theme.text,
      fontSize: 8,
      letterSpacing: 1.2,
      ...fontRole("body", spec, { fontWeight: 700 })
    }),
    box({ position: "absolute", left: 69, bottom: 55, width: 160, height: 1, backgroundColor: theme.text, opacity: 0.55 }),
    box({ position: "absolute", right: 83, bottom: 55, width: 160, height: 1, backgroundColor: theme.text, opacity: 0.55 })
  ]);
}

// templates/beautiful/grove-organic-brief.mjs
var templateId23 = "grove-organic-brief";
var rendererContract23 = {
  template_id: templateId23,
  renderer_id: `artboard_satori.${templateId23}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "grove",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/grove-1.png"
};
function colors23(spec) {
  return {
    background: "#0D281A",
    title: "#F0E7D2",
    muted: "#A37745",
    faint: "#1A3A27"
  };
}
function text23(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list9(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderGroveOrganicBrief(spec) {
  const theme = colors23(spec);
  const metrics = list9(spec, "metrics", ["03", "A calm year", "Notes"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.background, overflow: "hidden" }, [
    TextBlock(text23(spec, "eyebrow", "GROVE NOTE / 2026").toUpperCase(), {
      position: "absolute",
      left: 96,
      top: 133,
      color: theme.muted,
      fontSize: 8,
      letterSpacing: 1.4,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    Title(text23(spec, "title", "[Presentation Title\nGoes Here]"), {
      position: "absolute",
      left: 96,
      top: 174,
      width: 438,
      color: theme.title,
      fontSize: 37,
      lineHeight: 1.02,
      ...fontRole("display", spec, { fontWeight: 400 })
    }),
    TextBlock(text23(spec, "subtitle", "A year of craft by cadence or control"), {
      position: "absolute",
      left: 98,
      top: 266,
      width: 310,
      color: theme.title,
      opacity: 0.72,
      fontSize: 10,
      lineHeight: 1.35,
      ...fontRole("body", spec, { fontWeight: 400 })
    }),
    TextBlock(metrics[0] || "03", {
      position: "absolute",
      right: 75,
      bottom: 34,
      color: theme.faint,
      opacity: 0.35,
      fontSize: 87,
      lineHeight: 0.9,
      ...fontRole("metric", spec, { fontWeight: 300 })
    }),
    TextBlock((metrics[1] || "Moment").toUpperCase(), {
      position: "absolute",
      left: 96,
      bottom: 69,
      color: theme.muted,
      fontSize: 7,
      letterSpacing: 1.3,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    box({ position: "absolute", left: 455, bottom: 34, width: 52, height: 2, backgroundColor: theme.title, opacity: 0.5 })
  ]);
}

// templates/beautiful/mat-midcentury-board.mjs
var templateId24 = "mat-midcentury-board";
var rendererContract24 = {
  template_id: templateId24,
  renderer_id: `artboard_satori.${templateId24}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "mat",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/mat-1.png"
};
function colors24(spec) {
  return {
    background: "#232E26",
    cream: "#EDE6D0",
    paper: "#F5EDD8",
    ink: "#121D17",
    accent: "#D47B3B"
  };
}
function text24(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list10(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderMatMidcenturyBoard(spec) {
  const theme = colors24(spec);
  const cards = list10(spec, "cards", ["Designed by Studio", "The precision studio tools that work alone."]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.background, overflow: "hidden" }, [
    TextBlock(text24(spec, "eyebrow", "STUDIO NOTE").toUpperCase(), {
      position: "absolute",
      left: 598,
      top: 26,
      color: theme.accent,
      fontSize: 7,
      letterSpacing: 1.1,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    Title(text24(spec, "title", "Craft\nMatters"), {
      position: "absolute",
      left: 55,
      top: 45,
      width: 310,
      color: theme.cream,
      lineHeight: 0.93,
      whiteSpace: "pre-line",
      ...fontRole("display", spec, { fontSize: 72, fontWeight: 900, textTransform: "none" })
    }),
    TextBlock(text24(spec, "subtitle", "Designed for the hands that build things."), {
      position: "absolute",
      left: 755,
      top: 112,
      width: 140,
      color: theme.cream,
      opacity: 0.68,
      lineHeight: 1.35,
      ...fontRole("body", spec, { fontSize: 9, fontWeight: 400 })
    }),
    box({ position: "absolute", left: 744, top: 167, width: 84, height: 1, backgroundColor: theme.cream, opacity: 0.32 }),
    box({ position: "absolute", left: 744, top: 175, width: 126, height: 1, backgroundColor: theme.cream, opacity: 0.22 }),
    box({ position: "absolute", left: 744, top: 183, width: 58, height: 1, backgroundColor: theme.cream, opacity: 0.22 }),
    box({ position: "absolute", left: 60, top: 280, width: 185, height: 104, backgroundColor: theme.paper, padding: 16, flexDirection: "column" }, [
      TextBlock(cards[0] || "Designed by", { color: theme.ink, lineHeight: 1.05, ...fontRole("label", spec, { fontSize: 14, fontWeight: 800 }) }),
      TextBlock(cards[1] || "Studio tools", { color: theme.ink, marginTop: 8, lineHeight: 1.25, ...fontRole("body", spec, { fontSize: 10, fontWeight: 600 }) })
    ]),
    TextBlock("MAT / 2026", {
      position: "absolute",
      right: 38,
      bottom: 23,
      color: theme.cream,
      opacity: 0.72,
      letterSpacing: 1,
      ...fontRole("metric", spec, { fontSize: 7, fontWeight: 500 })
    }),
    box({ position: "absolute", left: 448, bottom: 22, width: 4, height: 2, backgroundColor: theme.cream, opacity: 0.7 }),
    box({ position: "absolute", left: 458, bottom: 22, width: 24, height: 2, backgroundColor: theme.cream, opacity: 0.45 }),
    box({ position: "absolute", left: 488, bottom: 22, width: 4, height: 2, backgroundColor: theme.cream, opacity: 0.7 }),
    box({ position: "absolute", right: 32, bottom: 38, width: 3, height: 3, backgroundColor: theme.cream, opacity: 0.5 }),
    box({ position: "absolute", right: 45, bottom: 38, width: 3, height: 3, backgroundColor: theme.cream, opacity: 0.5 }),
    box({ position: "absolute", right: 58, bottom: 38, width: 3, height: 3, backgroundColor: theme.cream, opacity: 0.5 })
  ]);
}

// templates/beautiful/dense-panel-grid.mjs
var templateId25 = "dense-panel-grid";
var rendererContract25 = {
  template_id: templateId25,
  renderer_id: `artboard_satori.${templateId25}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "neo-grid-bold",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/neo-grid-bold-1.png"
};
function colors25(spec) {
  return {
    black: "#0A0A0A",
    neon: "#E6FF3D",
    paper: "#F5F4EF",
    muted: "#464646"
  };
}
function text25(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list11(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderDensePanelGrid(spec) {
  const theme = colors25(spec);
  const metrics = list11(spec, "metrics", ["THE FUTURE OF DATA-DRIVEN FINANCE", "Q2 2026 DIGITS"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.paper, overflow: "hidden" }, [
    box({ position: "absolute", left: 0, top: 0, width: 255, height: 540, backgroundColor: theme.black }),
    box({ position: "absolute", left: 36, top: 42, width: 168, height: 376, borderWidth: 1, borderColor: "#1F1F1F" }),
    box({ position: "absolute", left: 72, top: 104, width: 96, height: 1, backgroundColor: "#2A2A2A" }),
    box({ position: "absolute", left: 72, top: 252, width: 96, height: 1, backgroundColor: "#2A2A2A" }),
    box({ position: "absolute", left: 72, top: 400, width: 96, height: 1, backgroundColor: "#2A2A2A" }),
    box({ position: "absolute", right: 0, top: 0, width: 308, height: 230, backgroundColor: theme.black }),
    box({ position: "absolute", right: 74, top: 54, width: 140, height: 120, borderWidth: 1, borderColor: "#202020" }),
    box({ position: "absolute", right: 112, top: 102, width: 64, height: 1, backgroundColor: "#2B2B2B" }),
    box({ position: "absolute", right: 112, top: 132, width: 64, height: 1, backgroundColor: "#2B2B2B" }),
    box({ position: "absolute", left: 256, top: 0, width: 390, height: 540, backgroundColor: theme.neon }),
    box(
      { position: "absolute", left: 278, top: 24, width: 38, height: 38, flexDirection: "row", flexWrap: "wrap" },
      Array.from({ length: 16 }).map((_, index) => box({ width: 8, height: 8, marginRight: 1, marginBottom: 1, backgroundColor: index % 2 ? theme.neon : theme.black }))
    ),
    box(
      { position: "absolute", right: 356, bottom: 64, width: 42, height: 42, flexDirection: "row", flexWrap: "wrap" },
      Array.from({ length: 9 }).map((_, index) => box({ width: 10, height: 10, marginRight: 2, marginBottom: 2, backgroundColor: index % 2 ? theme.neon : theme.black }))
    ),
    Title(text25(spec, "title", metrics[0] || "THE FUTURE OF DATA-DRIVEN FINANCE").toUpperCase(), {
      position: "absolute",
      left: 285,
      top: 305,
      width: 292,
      color: theme.black,
      lineHeight: 0.94,
      ...fontRole("display", spec, { fontSize: 24, fontWeight: 900, textTransform: "none" })
    }),
    TextBlock(text25(spec, "eyebrow", "08 / 13"), {
      position: "absolute",
      left: 20,
      bottom: 48,
      color: theme.paper,
      ...fontRole("metric", spec, { fontSize: 8, fontWeight: 600 })
    }),
    TextBlock((metrics[1] || "Q2 DIGITS").toUpperCase(), {
      position: "absolute",
      right: 32,
      bottom: 42,
      color: theme.black,
      lineHeight: 1.25,
      ...fontRole("label", spec, { fontSize: 9, fontWeight: 700 })
    }),
    TextBlock(text25(spec, "subtitle", "All rights reserved."), {
      position: "absolute",
      right: 40,
      bottom: 25,
      color: theme.muted,
      ...fontRole("body", spec, { fontSize: 7, fontWeight: 400 })
    })
  ]);
}

// templates/beautiful/people-platform-manifesto.mjs
var templateId26 = "people-platform-manifesto";
var rendererContract26 = {
  template_id: templateId26,
  renderer_id: `artboard_satori.${templateId26}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "peoples-platform",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/peoples-platform-1.png"
};
function colors26(spec) {
  return {
    blue: "#322AE8",
    orange: "#FF7A3D",
    cream: "#F6EACD",
    white: "#FFFFFF"
  };
}
function text26(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list12(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderPeoplePlatformManifesto(spec) {
  const theme = colors26(spec);
  const platforms = list12(spec, "platforms", ["Prepared by the team", "May 2026", "Version 01"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.blue, overflow: "hidden" }, [
    box({ position: "absolute", left: 42, top: 42, right: 42, bottom: 42, borderWidth: 3, borderColor: theme.cream }),
    TextBlock(text26(spec, "eyebrow", "STRATEGIC REVIEW \xB7 INTERNAL").toUpperCase(), {
      position: "absolute",
      left: 392,
      top: 66,
      color: theme.cream,
      fontSize: 8,
      letterSpacing: 1.4,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    Title(text26(spec, "title", "QUARTERLY\nREVIEW").toUpperCase(), {
      position: "absolute",
      left: 161,
      top: 172,
      width: 660,
      color: theme.cream,
      fontSize: 67,
      lineHeight: 0.82,
      whiteSpace: "pre-line",
      ...fontRole("display", spec, { fontWeight: 900 })
    }),
    Title(text26(spec, "title", "QUARTERLY\nREVIEW").toUpperCase(), {
      position: "absolute",
      left: 153,
      top: 164,
      width: 660,
      color: theme.orange,
      fontSize: 67,
      lineHeight: 0.82,
      whiteSpace: "pre-line",
      ...fontRole("display", spec, { fontWeight: 900 })
    }),
    TextBlock(text26(spec, "subtitle", "A PRESENTATION TEMPLATE").toUpperCase(), {
      position: "absolute",
      left: 265,
      top: 326,
      color: theme.cream,
      fontSize: 24,
      ...fontRole("body", spec, { fontWeight: 900 })
    }),
    TextBlock(platforms.join("  \xB7  ").toUpperCase(), {
      position: "absolute",
      left: 331,
      top: 371,
      color: theme.cream,
      fontSize: 8,
      letterSpacing: 1.1,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    TextBlock(text26(spec, "stamp", "VOL. 01").toUpperCase(), {
      position: "absolute",
      right: 67,
      top: 66,
      color: theme.cream,
      fontSize: 10,
      ...fontRole("metric", spec, { fontWeight: 700 })
    })
  ]);
}

// templates/beautiful/annotated-field-board.mjs
var templateId27 = "annotated-field-board";
var rendererContract27 = {
  template_id: templateId27,
  renderer_id: `artboard_satori.${templateId27}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "pin-and-paper",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/pin-and-paper-1.png"
};
function colors27(spec) {
  return {
    paper: "#EDE66B",
    blue: "#1E4FDB",
    ink: "#1C2E33",
    muted: "#60684D"
  };
}
function text27(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list13(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function pin(theme, left, top, rotate = 0) {
  return box({ position: "absolute", left, top, width: 120, height: 26, transform: `rotate(${rotate}deg)`, flexDirection: "row", alignItems: "center" }, [
    box({ width: 16, height: 16, borderRadius: 999, borderWidth: 2, borderColor: theme.blue }),
    box({ width: 86, height: 2, backgroundColor: theme.blue }),
    box({ width: 8, height: 8, borderRadius: 999, backgroundColor: theme.blue })
  ]);
}
function renderAnnotatedFieldBoard(spec) {
  const theme = colors27(spec);
  const notes = list13(spec, "notes", ["For the team", "You people can act"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.paper, overflow: "hidden" }, [
    TextBlock(text27(spec, "eyebrow", "A FIELD ISSUE \xB7 VOL. 1").toUpperCase(), {
      position: "absolute",
      left: 66,
      top: 48,
      color: theme.blue,
      fontSize: 8,
      letterSpacing: 1.2,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    Title(text27(spec, "title", "Kept\nthings"), {
      position: "absolute",
      left: 96,
      top: 181,
      width: 330,
      color: theme.blue,
      fontSize: 60,
      lineHeight: 1,
      whiteSpace: "pre-line",
      ...fontRole("display", spec, { fontWeight: 800 })
    }),
    TextBlock(notes[0] || "For the team", {
      position: "absolute",
      right: 94,
      top: 318,
      width: 166,
      color: theme.ink,
      fontSize: 15,
      lineHeight: 1.22,
      transform: "rotate(-6deg)",
      ...fontRole("body", spec, { fontWeight: 700 })
    }),
    TextBlock((notes[1] || "Surveyed all spring").toUpperCase(), {
      position: "absolute",
      left: 98,
      bottom: 56,
      color: theme.muted,
      fontSize: 8,
      letterSpacing: 1,
      ...fontRole("metric", spec, { fontWeight: 600 })
    }),
    pin(theme, 772, 68, -10),
    pin(theme, 760, 338, 8),
    TextBlock("01 / 10", { position: "absolute", right: 56, bottom: 39, color: theme.blue, fontSize: 8, ...fontRole("label", spec) })
  ]);
}

// templates/beautiful/pink-nocturne-feature.mjs
var templateId28 = "pink-nocturne-feature";
var rendererContract28 = {
  template_id: templateId28,
  renderer_id: `artboard_satori.${templateId28}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "pink-script",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/pink-script-1.png"
};
function colors28(spec) {
  return {
    black: "#100C12",
    pink: "#E63793",
    white: "#F5E8EC",
    muted: "#9C7A86"
  };
}
function text28(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list14(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderPinkNocturneFeature(spec) {
  const theme = colors28(spec);
  const sections = list14(spec, "sections", ["Edition", "Director", "Locale", "Date"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.black, overflow: "hidden" }, [
    box({ position: "absolute", left: 210, top: 86, width: 540, height: 360, borderRadius: 999, backgroundColor: "#FFFFFF", opacity: 0.04 }),
    TextBlock(text28(spec, "eyebrow", "MAISON NOCTURNE").toUpperCase(), {
      position: "absolute",
      left: 34,
      top: 40,
      color: theme.pink,
      fontSize: 8,
      letterSpacing: 1.4,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    TextBlock("A FIELD REPORT ON LATE-NIGHT CULTURE", {
      position: "absolute",
      left: 292,
      top: 82,
      color: theme.muted,
      fontSize: 8,
      letterSpacing: 2,
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    Title(text28(spec, "title", "After\nHours."), {
      position: "absolute",
      left: 336,
      top: 153,
      width: 340,
      color: theme.white,
      fontSize: 70,
      lineHeight: 0.93,
      whiteSpace: "pre-line",
      ...fontRole("display", spec, { fontWeight: 800 })
    }),
    TextBlock(text28(spec, "quote", "After"), {
      position: "absolute",
      left: 336,
      top: 132,
      color: theme.pink,
      fontSize: 78,
      lineHeight: 0.9,
      ...fontRole("display", spec, { fontWeight: 800 })
    }),
    ...sections.slice(0, 4).map(
      (item, index) => TextBlock(item, {
        position: "absolute",
        left: 33 + index * 235,
        bottom: 47,
        color: index === 3 ? theme.pink : theme.white,
        fontSize: 12,
        lineHeight: 1.1,
        ...fontRole("body", spec, { fontWeight: 700 })
      })
    ),
    TextBlock(text28(spec, "pageno", "01 / 09"), { position: "absolute", right: 36, bottom: 23, color: theme.white, fontSize: 9, ...fontRole("metric", spec) })
  ]);
}

// templates/beautiful/playful-indie-launch.mjs
var templateId29 = "playful-indie-launch";
var rendererContract29 = {
  template_id: templateId29,
  renderer_id: `artboard_satori.${templateId29}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "playful",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/playful-1.png"
};
function colors29(spec) {
  return {
    peach: "#F2C69D",
    ink: "#171717",
    cream: "#F7DFB8",
    accent: "#111111"
  };
}
function text29(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list15(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderPlayfulIndieLaunch(spec) {
  const theme = colors29(spec);
  const stats = list15(spec, "stats", ["02-05-26", "Special drop", "No. 4"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.peach, overflow: "hidden" }, [
    Title(stats[0] || "02-05-26", {
      position: "absolute",
      left: 92,
      top: 200,
      width: 330,
      color: theme.ink,
      fontSize: 53,
      lineHeight: 0.92,
      ...fontRole("metric", spec, { fontWeight: 900 })
    }),
    Title(text29(spec, "title", "Creative Direction & Visual\nSystem"), {
      position: "absolute",
      left: 92,
      top: 267,
      width: 380,
      color: theme.ink,
      fontSize: 29,
      lineHeight: 1.02,
      ...fontRole("display", spec, { fontWeight: 900 })
    }),
    TextBlock(text29(spec, "subtitle", "A generous presentation for early-stage launches."), {
      position: "absolute",
      left: 96,
      top: 336,
      width: 285,
      color: theme.ink,
      fontSize: 10,
      lineHeight: 1.25,
      ...fontRole("body", spec, { fontWeight: 500 })
    }),
    box({ position: "absolute", right: 148, top: 136, width: 74, height: 104, borderRadius: 999, borderWidth: 2, borderColor: theme.ink, transform: "rotate(10deg)", alignItems: "center", justifyContent: "center" }, [
      box({ width: 44, height: 65, borderRadius: 999, backgroundColor: theme.ink, transform: "rotate(12deg)" })
    ]),
    box({ position: "absolute", right: 242, bottom: 84, width: 54, height: 70, borderRadius: 999, borderWidth: 2, borderColor: theme.ink, transform: "rotate(14deg)" }),
    TextBlock(text29(spec, "eyebrow", "SPECIAL DROP").toUpperCase(), {
      position: "absolute",
      right: 129,
      top: 256,
      color: theme.ink,
      fontSize: 8,
      letterSpacing: 1.4,
      transform: "rotate(90deg)",
      ...fontRole("label", spec, { fontWeight: 700 })
    }),
    TextBlock(stats[1] || "Special drop", { position: "absolute", right: 38, bottom: 24, color: theme.ink, fontSize: 8, ...fontRole("label", spec) })
  ]);
}

// templates/beautiful/retro-ui-dashboard.mjs
var templateId30 = "retro-ui-dashboard";
var rendererContract30 = {
  template_id: templateId30,
  renderer_id: `artboard_satori.${templateId30}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "retro-windows",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/retro-windows-1.png"
};
function colors30(spec) {
  return {
    desk: "#8B8B87",
    window: "#D8D4C7",
    blue: "#1100A8",
    ink: "#202020"
  };
}
function text30(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list16(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderRetroUiDashboard(spec) {
  const theme = colors30(spec);
  const panels = list16(spec, "panels", ["Build status: OK", "Open issues: 12", "Owner: Platform"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.desk, overflow: "hidden" }, [
    box({ position: "absolute", left: 338, top: 12, width: 326, height: 472, backgroundColor: theme.window, borderWidth: 2, borderColor: theme.ink, flexDirection: "column" }, [
      box({ width: "100%", height: 18, backgroundColor: theme.blue, flexDirection: "row", alignItems: "center", paddingLeft: 8 }, [
        TextBlock(text30(spec, "window_title", "SVGLIDE.EXE"), { color: "#FFFFFF", fontSize: 8, ...fontRole("label", spec, { fontWeight: 700 }) })
      ]),
      box({ flex: 1, alignItems: "center", justifyContent: "center", flexDirection: "column" }, [
        TextBlock("\u2605", { color: theme.ink, fontSize: 16, marginBottom: 38, ...fontRole("metric", spec, { fontWeight: 900 }) }),
        Title(text30(spec, "title", "QUARTERLY OVERVIEW").toUpperCase(), { color: theme.blue, fontSize: 18, lineHeight: 1, marginBottom: 12, ...fontRole("display", spec, { fontWeight: 900 }) }),
        TextBlock(text30(spec, "subtitle", "Compact product status window."), { width: 220, textAlign: "center", color: theme.ink, fontSize: 9, lineHeight: 1.3, marginBottom: 18, ...fontRole("body", spec) }),
        ...panels.slice(0, 3).map((item) => TextBlock(item, { width: 206, backgroundColor: "#F4F1E8", borderWidth: 1, borderColor: theme.ink, padding: "4px 6px", color: theme.ink, fontSize: 8, marginBottom: 5, ...fontRole("label", spec, { fontWeight: 600 }) }))
      ])
    ]),
    TextBlock(text30(spec, "status", "READY"), { position: "absolute", right: 18, bottom: 15, color: "#FFFFFF", fontSize: 8, ...fontRole("metric", spec) })
  ]);
}

// templates/beautiful/retro-zine-spread.mjs
var templateId31 = "retro-zine-spread";
var rendererContract31 = {
  template_id: templateId31,
  renderer_id: `artboard_satori.${templateId31}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "retro-zine",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/retro-zine-1.png"
};
function colors31(spec) {
  return {
    paper: "#C9BDA2",
    green: "#00A66A",
    ink: "#202020",
    accent: "#F4F0E5"
  };
}
function text31(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list17(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderRetroZineSpread(spec) {
  const theme = colors31(spec);
  const notes = list17(spec, "notes", ["Never again", "Always remember"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.paper, overflow: "hidden" }, [
    TextBlock(text31(spec, "eyebrow", "SMALL STORIES").toUpperCase(), { position: "absolute", left: 372, top: 146, color: theme.green, fontSize: 9, letterSpacing: 1.1, ...fontRole("label", spec, { fontWeight: 800 }) }),
    Title(text31(spec, "title", "NEXUS\nVENTURES").toUpperCase(), { position: "absolute", left: 354, top: 170, width: 250, color: theme.green, fontSize: 45, lineHeight: 0.9, textAlign: "center", ...fontRole("display", spec, { fontWeight: 900 }) }),
    box({ position: "absolute", left: 438, top: 296, width: 52, height: 52, borderRadius: 999, backgroundColor: theme.ink, alignItems: "center", justifyContent: "center" }, [
      box({ width: 24, height: 24, borderRadius: 999, backgroundColor: theme.accent })
    ]),
    TextBlock(notes[0] || "Never again", { position: "absolute", left: 338, top: 345, width: 120, textAlign: "right", color: theme.ink, fontSize: 7, ...fontRole("body", spec, { fontWeight: 600 }) }),
    TextBlock(notes[1] || "Always remember", { position: "absolute", left: 498, top: 345, width: 128, color: theme.ink, fontSize: 7, ...fontRole("body", spec, { fontWeight: 600 }) }),
    TextBlock(text31(spec, "stamp", "2026"), { position: "absolute", left: 452, top: 382, color: theme.green, fontSize: 18, ...fontRole("metric", spec, { fontWeight: 900 }) }),
    TextBlock(text31(spec, "quote", "Never again. Always remember."), { position: "absolute", left: 394, top: 356, width: 170, color: theme.ink, fontSize: 6, textAlign: "center", ...fontRole("label", spec, { fontWeight: 700 }) })
  ]);
}

// templates/beautiful/sticky-workshop-board.mjs
var templateId32 = "sticky-workshop-board";
var rendererContract32 = {
  template_id: templateId32,
  renderer_id: `artboard_satori.${templateId32}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "scatterbrain",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/scatterbrain-1.png"
};
function colors32(spec) {
  return {
    paper: "#D9C9AD",
    yellow: "#F8D444",
    blue: "#9DC7E8",
    green: "#BDE083",
    ink: "#1C1C1C"
  };
}
function text32(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list18(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function note(item, style, spec) {
  return box({ position: "absolute", width: 156, height: 66, padding: 9, transform: style.transform, backgroundColor: style.color, left: style.left, top: style.top, justifyContent: "center", alignItems: "center" }, [
    TextBlock(item, { color: "#111111", fontSize: 16, lineHeight: 1, textAlign: "center", ...fontRole("label", spec, { fontWeight: 800 }) })
  ]);
}
function renderStickyWorkshopBoard(spec) {
  const theme = colors32(spec);
  const postits = list18(spec, "postits", ["Workshop map", "Ask a good question", "Prototype fast"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.paper, overflow: "hidden" }, [
    note(postits[1] || "User pain", { left: 322, top: 176, color: theme.green, transform: "rotate(-8deg)" }, spec),
    note(text32(spec, "title", postits[0] || "Workshop map"), { left: 407, top: 164, color: theme.yellow, transform: "rotate(2deg)" }, spec),
    note(postits[2] || "Launch test", { left: 517, top: 142, color: theme.blue, transform: "rotate(8deg)" }, spec),
    TextBlock(text32(spec, "title", postits[0] || "Workshop map"), {
      position: "absolute",
      left: 423,
      top: 188,
      width: 126,
      color: theme.ink,
      fontSize: 18,
      lineHeight: 1,
      textAlign: "center",
      transform: "rotate(2deg)",
      ...fontRole("display", spec, { fontWeight: 900 })
    }),
    TextBlock(text32(spec, "eyebrow", "BRAINSTORM BOARD").toUpperCase(), { position: "absolute", left: 389, top: 285, color: theme.ink, fontSize: 8, letterSpacing: 1.1, ...fontRole("label", spec, { fontWeight: 700 }) }),
    TextBlock(text32(spec, "subtitle", "Collect your thoughts, pin them down, and make the big problem small."), { position: "absolute", left: 348, top: 306, width: 266, color: theme.ink, fontSize: 9, lineHeight: 1.4, textAlign: "center", ...fontRole("body", spec) }),
    TextBlock(String(postits.length).padStart(2, "0"), { position: "absolute", right: 30, bottom: 22, color: theme.ink, fontSize: 8, ...fontRole("metric", spec) })
  ]);
}

// templates/beautiful/stencil-field-manual.mjs
var templateId33 = "stencil-field-manual";
var rendererContract33 = {
  template_id: templateId33,
  renderer_id: `artboard_satori.${templateId33}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "stencil-tablet",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/stencil-tablet-1.png"
};
function colors33(spec) {
  return {
    paper: "#EDE6D1",
    ink: "#141414",
    green: "#0E7F69",
    orange: "#FF6F2C"
  };
}
function text33(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list19(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderStencilFieldManual(spec) {
  const theme = colors33(spec);
  const principles = list19(spec, "principles", ["Archive", "Method", "Reading"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.paper, overflow: "hidden" }, [
    TextBlock(text33(spec, "eyebrow", "AGENCY NAME \xB7 PARTNER NAME").toUpperCase(), { position: "absolute", left: 430, top: 34, color: theme.ink, fontSize: 8, letterSpacing: 1.2, ...fontRole("label", spec, { fontWeight: 900 }) }),
    Title(text33(spec, "title", "BOLD BY\nDESIGN.").toUpperCase(), { position: "absolute", left: 458, top: 292, width: 420, color: theme.ink, fontSize: 54, lineHeight: 0.87, ...fontRole("display", spec, { fontWeight: 900 }) }),
    box({ position: "absolute", right: -34, top: 70, width: 132, height: 104, borderRadius: 999, backgroundColor: theme.green, transform: "rotate(44deg)" }),
    box({ position: "absolute", right: 24, top: 145, width: 116, height: 80, borderRadius: 999, backgroundColor: theme.green, transform: "rotate(8deg)" }),
    box({ position: "absolute", left: 462, bottom: 39, width: 90, height: 2, backgroundColor: theme.ink }),
    box({ position: "absolute", left: 462, bottom: 34, width: 150, height: 2, backgroundColor: theme.ink, opacity: 0.45 }),
    box({ position: "absolute", left: 462, bottom: 29, width: 112, height: 2, backgroundColor: theme.ink, opacity: 0.35 }),
    TextBlock(principles.slice(0, 2).join(" \xB7 ").toUpperCase(), { position: "absolute", left: 472, bottom: 52, color: theme.ink, fontSize: 9, letterSpacing: 1, ...fontRole("body", spec, { fontWeight: 700 }) }),
    box({ position: "absolute", left: 458, bottom: 52, width: 12, height: 12, backgroundColor: theme.orange }),
    TextBlock(text33(spec, "footer", "29 \xB7 IV \xB7 2026"), { position: "absolute", right: 47, bottom: 38, color: theme.ink, fontSize: 10, ...fontRole("metric", spec, { fontWeight: 700 }) })
  ]);
}

// templates/beautiful/vellum-scholar-brief.mjs
var templateId34 = "vellum-scholar-brief";
var rendererContract34 = {
  template_id: templateId34,
  renderer_id: `artboard_satori.${templateId34}`,
  status: "needs_review",
  renderer_stage: "dedicated_sample",
  default_selectable: false,
  selection_scope: "experimental",
  source_family: "vellum",
  required_font_roles: ["display", "body", "label", "metric"],
  reference_screenshot: "beautiful-html-templates/screenshots/vellum-1.png"
};
function colors34(spec) {
  return {
    navy: "#2A3870",
    yellow: "#F4E55C",
    muted: "#6D7BA5",
    paper: "#F8F5E8"
  };
}
function text34(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list20(spec, key, fallback = []) {
  const value = spec.content?.[key];
  return Array.isArray(value) && value.length ? value : fallback;
}
function renderVellumScholarBrief(spec) {
  const theme = colors34(spec);
  const stats = list20(spec, "stats", ["42 papers", "8 interviews", "3 scenarios"]);
  return box({ width: 960, height: 540, position: "relative", backgroundColor: theme.navy, overflow: "hidden" }, [
    TextBlock(text34(spec, "eyebrow", "POLICY BRIEF").toUpperCase(), { position: "absolute", left: 386, top: 224, color: theme.muted, fontSize: 8, letterSpacing: 1.4, ...fontRole("label", spec, { fontWeight: 700 }) }),
    Title(text34(spec, "title", "On Restraint"), { position: "absolute", left: 119, top: 255, width: 540, color: theme.yellow, lineHeight: 1, ...fontRole("display", spec, { fontSize: 64, fontWeight: 400, textTransform: "none" }) }),
    TextBlock(text34(spec, "subtitle", "Field notes on the discipline of less."), { position: "absolute", left: 337, top: 326, width: 330, color: theme.muted, textAlign: "center", lineHeight: 1.3, ...fontRole("body", spec, { fontSize: 11 }) }),
    TextBlock(stats.join(" \xB7 "), { position: "absolute", left: 42, bottom: 32, color: theme.muted, ...fontRole("metric", spec, { fontSize: 8, fontWeight: 500 }) }),
    box({ position: "absolute", left: 444, bottom: 20, width: 24, height: 2, backgroundColor: theme.paper, opacity: 0.7 }),
    TextBlock("01", { position: "absolute", right: 36, bottom: 29, color: theme.muted, fontSize: 8, ...fontRole("label", spec) })
  ]);
}

// templates/beautiful/index.mjs
var DEDICATED_RENDERERS = /* @__PURE__ */ new Map([
  [
    rendererContract.template_id,
    {
      contract: rendererContract,
      render: renderExecutiveDashboard
    }
  ],
  [
    rendererContract2.template_id,
    {
      contract: rendererContract2,
      render: renderIntelligenceBrief
    }
  ],
  [
    rendererContract3.template_id,
    {
      contract: rendererContract3,
      render: renderPosterStatPunch
    }
  ],
  [
    rendererContract4.template_id,
    {
      contract: rendererContract4,
      render: renderCoralMagazineFeature
    }
  ],
  [
    rendererContract5.template_id,
    {
      contract: rendererContract5,
      render: renderSoftEditorialFeature
    }
  ],
  [
    rendererContract6.template_id,
    {
      contract: rendererContract6,
      render: renderTritoneEditorialSpread
    }
  ],
  [
    rendererContract7.template_id,
    {
      contract: rendererContract7,
      render: renderPixelOrbitConsole
    }
  ],
  [
    rendererContract8.template_id,
    {
      contract: rendererContract8,
      render: renderBiennaleProgrammePoster
    }
  ],
  [
    rendererContract9.template_id,
    {
      contract: rendererContract9,
      render: renderBlockFrameGrid
    }
  ],
  [
    rendererContract10.template_id,
    {
      contract: rendererContract10,
      render: renderBroadsideEditorialQuote
    }
  ],
  [
    rendererContract11.template_id,
    {
      contract: rendererContract11,
      render: renderCartesianArchitecturalSpec
    }
  ],
  [
    rendererContract12.template_id,
    {
      contract: rendererContract12,
      render: renderLongTablePrintedProgram
    }
  ],
  [
    rendererContract13.template_id,
    {
      contract: rendererContract13,
      render: renderMonochromeLedgerBriefing
    }
  ],
  [
    rendererContract14.template_id,
    {
      contract: rendererContract14,
      render: renderCapsuleCardSystem
    }
  ],
  [
    rendererContract15.template_id,
    {
      contract: rendererContract15,
      render: renderCreativeModeGrid
    }
  ],
  [
    rendererContract16.template_id,
    {
      contract: rendererContract16,
      render: renderDaisyWorkshopPlaybook
    }
  ],
  [
    rendererContract17.template_id,
    {
      contract: rendererContract17,
      render: renderEmeraldEditorialCover
    }
  ],
  [
    rendererContract18.template_id,
    {
      contract: rendererContract18,
      render: renderTrendGridReport
    }
  ],
  [
    rendererContract19.template_id,
    {
      contract: rendererContract19,
      render: renderProductRibbon
    }
  ],
  [
    rendererContract20.template_id,
    {
      contract: rendererContract20,
      render: renderBrutalistMatrix
    }
  ],
  [
    rendererContract21.template_id,
    {
      contract: rendererContract21,
      render: renderTypeMassPoster
    }
  ],
  [
    rendererContract22.template_id,
    {
      contract: rendererContract22,
      render: renderSerifStatEditorial
    }
  ],
  [
    rendererContract23.template_id,
    {
      contract: rendererContract23,
      render: renderGroveOrganicBrief
    }
  ],
  [
    rendererContract24.template_id,
    {
      contract: rendererContract24,
      render: renderMatMidcenturyBoard
    }
  ],
  [
    rendererContract25.template_id,
    {
      contract: rendererContract25,
      render: renderDensePanelGrid
    }
  ],
  [
    rendererContract26.template_id,
    {
      contract: rendererContract26,
      render: renderPeoplePlatformManifesto
    }
  ],
  [
    rendererContract27.template_id,
    {
      contract: rendererContract27,
      render: renderAnnotatedFieldBoard
    }
  ],
  [
    rendererContract28.template_id,
    {
      contract: rendererContract28,
      render: renderPinkNocturneFeature
    }
  ],
  [
    rendererContract29.template_id,
    {
      contract: rendererContract29,
      render: renderPlayfulIndieLaunch
    }
  ],
  [
    rendererContract30.template_id,
    {
      contract: rendererContract30,
      render: renderRetroUiDashboard
    }
  ],
  [
    rendererContract31.template_id,
    {
      contract: rendererContract31,
      render: renderRetroZineSpread
    }
  ],
  [
    rendererContract32.template_id,
    {
      contract: rendererContract32,
      render: renderStickyWorkshopBoard
    }
  ],
  [
    rendererContract33.template_id,
    {
      contract: rendererContract33,
      render: renderStencilFieldManual
    }
  ],
  [
    rendererContract34.template_id,
    {
      contract: rendererContract34,
      render: renderVellumScholarBrief
    }
  ]
]);
var EVALUATION_RENDERERS = new Map(
  evaluationTemplateIds.map((templateId35) => [
    templateId35,
    {
      contract: evaluationRendererContract(templateId35),
      render: renderEvaluationBeautifulStub
    }
  ])
);
function productionLike(spec = {}) {
  return spec.template_status === "production" || spec.selection_scope === "production" || spec.asset_status === "production";
}
function renderBeautifulTemplate(spec = {}) {
  const templateId35 = spec.template_id;
  const dedicated = DEDICATED_RENDERERS.get(templateId35);
  if (dedicated) {
    return dedicated.render(spec);
  }
  const evaluation = EVALUATION_RENDERERS.get(templateId35);
  if (evaluation) {
    return evaluation.render(spec, evaluation.contract);
  }
  if (productionLike(spec)) {
    throw new Error(`missing dedicated beautiful renderer for production template_id: ${templateId35}`);
  }
  return null;
}

// templates/p0-templates.mjs
var CANVAS = { width: 960, height: 540 };
var DEFAULT_FONT_FAMILY = "SVGlideDefault";
function colors35(spec) {
  const source = spec.theme?.colors || {};
  return {
    background: source.background || "#0F172A",
    panel: source.panel || "#111827",
    primary: source.primary || "#38BDF8",
    accent: source.accent || "#A78BFA",
    text: source.text || "#F8FAFC",
    muted: source.muted || "#CBD5E1",
    surface: source.surface || source.panel || "#111827"
  };
}
function text35(spec, key, fallback = "") {
  const value = spec.content?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
function list21(spec, key) {
  const value = spec.content?.[key];
  return Array.isArray(value) ? value.filter((item) => typeof item === "string" && item.trim()).map((item) => item.trim()) : [];
}
function firstList(spec, keys, fallback = []) {
  for (const key of keys) {
    const values = list21(spec, key);
    if (values.length) return values;
  }
  return fallback;
}
function themeSize(spec, key, fallback) {
  const value = spec.theme?.typography?.[key];
  return typeof value === "number" ? value : fallback;
}
function pageShell(spec, children) {
  const theme = colors35(spec);
  return box(
    {
      width: CANVAS.width,
      height: CANVAS.height,
      position: "relative",
      flexDirection: "column",
      backgroundColor: theme.background,
      color: theme.text,
      fontFamily: DEFAULT_FONT_FAMILY,
      padding: 56
    },
    children
  );
}
function pageHeader(spec, { titleWidth = 720, titleSize = null, subtitleKey = "subtitle" } = {}) {
  const theme = colors35(spec);
  return box({ flexDirection: "column", marginBottom: 28 }, [
    Badge(text35(spec, "eyebrow", "").toUpperCase(), {
      color: theme.primary,
      fontSize: 16,
      fontWeight: 800,
      marginBottom: 12
    }),
    Title(text35(spec, "title", "Untitled"), {
      width: titleWidth,
      color: theme.text,
      fontSize: titleSize || themeSize(spec, "title", 42),
      fontWeight: 850,
      lineHeight: 1.08,
      marginBottom: 14
    }),
    Subtitle(text35(spec, subtitleKey, ""), {
      width: Math.min(titleWidth, 700),
      color: theme.muted,
      fontSize: themeSize(spec, "subtitle", 21),
      lineHeight: 1.22
    })
  ]);
}
function numberedRows(items, theme, { start = 1, max = 6 } = {}) {
  return items.slice(0, max).map(
    (item, index) => box(
      {
        width: "100%",
        minHeight: 46,
        flexDirection: "row",
        alignItems: "center",
        marginBottom: 12,
        backgroundColor: theme.panel,
        padding: "11px 14px"
      },
      [
        TextBlock(String(index + start).padStart(2, "0"), {
          width: 48,
          color: theme.primary,
          fontSize: 18,
          fontWeight: 850
        }),
        TextBlock(item, {
          flex: 1,
          color: theme.text,
          fontSize: 20,
          fontWeight: 650,
          lineHeight: 1.15
        })
      ]
    )
  );
}
function smallCard(label, value, theme, style = {}) {
  return box(
    {
      width: 184,
      minHeight: 112,
      flexDirection: "column",
      backgroundColor: theme.panel,
      padding: 18,
      ...style
    },
    [
      TextBlock(label, { color: theme.muted, fontSize: 15, fontWeight: 700, marginBottom: 14 }),
      TextBlock(value, { color: theme.text, fontSize: 25, fontWeight: 850, lineHeight: 1.05 })
    ]
  );
}
function coverHero(spec) {
  const theme = colors35(spec);
  const chips = list21(spec, "chips").slice(0, 4);
  return box(
    {
      width: CANVAS.width,
      height: CANVAS.height,
      position: "relative",
      flexDirection: "column",
      backgroundColor: theme.background,
      color: theme.text,
      fontFamily: DEFAULT_FONT_FAMILY,
      padding: 72
    },
    [
      box({
        position: "absolute",
        left: 724,
        top: 36,
        width: 192,
        height: 192,
        borderRadius: 96,
        backgroundColor: theme.accent,
        opacity: 0.28
      }),
      box({
        width: 704,
        minHeight: 356,
        flexDirection: "column",
        backgroundColor: theme.panel,
        opacity: 0.96,
        padding: 28
      }, [
        Badge(text35(spec, "eyebrow", "SVGLIDE ARTBOARD"), {
          color: theme.primary,
          marginBottom: 18
        }),
        Title(text35(spec, "title", "Untitled"), {
          color: theme.text,
          fontSize: 58,
          fontWeight: 800,
          lineHeight: 1.05,
          marginBottom: 20
        }),
        Subtitle(text35(spec, "subtitle", ""), {
          color: theme.muted,
          fontSize: 24,
          fontWeight: 500,
          lineHeight: 1.25
        })
      ]),
      box(
        {
          position: "absolute",
          left: 84,
          top: 444,
          flexDirection: "row",
          gap: 14
        },
        chips.map(
          (chip) => Chip(chip, {
            backgroundColor: theme.primary,
            color: theme.text,
            opacity: 0.86
          })
        )
      )
    ]
  );
}
function comparisonCards(spec) {
  const theme = colors35(spec);
  const leftPoints = list21(spec, "left_points").slice(0, 3);
  const rightPoints = list21(spec, "right_points").slice(0, 3);
  const point = (value, color) => box({ flexDirection: "row", alignItems: "center", marginBottom: 18 }, [
    box({ width: 10, height: 10, borderRadius: 5, backgroundColor: color, marginRight: 14 }),
    TextBlock(value, { color: theme.muted, fontSize: 20, fontWeight: 500, lineHeight: 1.2 })
  ]);
  return box(
    {
      width: CANVAS.width,
      height: CANVAS.height,
      position: "relative",
      flexDirection: "column",
      backgroundColor: theme.background,
      color: theme.text,
      fontFamily: DEFAULT_FONT_FAMILY,
      padding: "52px 64px"
    },
    [
      Title(text35(spec, "title", "Comparison"), { color: theme.text, fontSize: 40, lineHeight: 1.1, marginBottom: 44 }),
      box({ flexDirection: "row", gap: 52 }, [
        box({ width: 390, height: 250, flexDirection: "column", backgroundColor: theme.panel, padding: 28 }, [
          Title(text35(spec, "left_title", "Before"), { color: theme.primary, fontSize: 24, lineHeight: 1.1, marginBottom: 28 }),
          ...leftPoints.map((item) => point(item, theme.primary))
        ]),
        box({ width: 390, height: 250, flexDirection: "column", backgroundColor: theme.panel, padding: 28 }, [
          Title(text35(spec, "right_title", "After"), { color: theme.accent, fontSize: 24, lineHeight: 1.1, marginBottom: 28 }),
          ...rightPoints.map((item) => point(item, theme.accent))
        ])
      ]),
      TextBlock(text35(spec, "conclusion", ""), {
        position: "absolute",
        left: 64,
        top: 414,
        width: 832,
        height: 66,
        padding: "20px 22px",
        backgroundColor: theme.primary,
        color: theme.text,
        opacity: 0.88,
        fontSize: 22,
        fontWeight: 700
      })
    ]
  );
}
function summaryFinal(spec) {
  const theme = colors35(spec);
  const takeaways = list21(spec, "takeaways").slice(0, 3);
  return box(
    {
      width: CANVAS.width,
      height: CANVAS.height,
      position: "relative",
      flexDirection: "column",
      backgroundColor: theme.background,
      color: theme.text,
      fontFamily: DEFAULT_FONT_FAMILY,
      padding: "64px 72px"
    },
    [
      box({ position: "absolute", left: 704, top: 54, width: 164, height: 164, borderRadius: 82, backgroundColor: theme.accent, opacity: 0.22 }),
      box({ position: "absolute", left: 712, top: 286, flexDirection: "row", alignItems: "flex-end", gap: 12 }, [
        box({ width: 18, height: 30, backgroundColor: theme.primary, opacity: 0.72 }),
        box({ width: 18, height: 48, backgroundColor: theme.primary, opacity: 0.86 }),
        box({ width: 18, height: 66, backgroundColor: theme.accent, opacity: 0.92 })
      ]),
      Badge(text35(spec, "eyebrow", "SUMMARY"), { color: theme.primary, fontSize: 18, fontWeight: 800, marginBottom: 24 }),
      Title(text35(spec, "title", "Summary"), { width: 700, color: theme.text, fontSize: 50, fontWeight: 850, lineHeight: 1.08, marginBottom: 24 }),
      Subtitle(text35(spec, "subtitle", ""), { width: 640, color: theme.muted, fontSize: 23, marginBottom: 34 }),
      box(
        { flexDirection: "row", gap: 18 },
        takeaways.map(
          (item, index) => StatCard({
            index: index + 1,
            label: item,
            color: theme.primary,
            textColor: theme.text,
            panelColor: theme.panel
          })
        )
      )
    ]
  );
}
function sectionTitle(spec) {
  const theme = colors35(spec);
  return pageShell(spec, [
    box({ position: "absolute", left: 72, top: 116, width: 8, height: 258, backgroundColor: theme.primary }),
    box({ position: "absolute", left: 734, top: 74, width: 148, height: 148, backgroundColor: theme.accent, opacity: 0.2 }),
    box({ position: "absolute", left: 734, top: 242, width: 148, height: 12, backgroundColor: theme.primary }),
    box({ marginLeft: 52, marginTop: 64 }, [pageHeader(spec, { titleWidth: 690, titleSize: 56 })])
  ]);
}
function agendaList(spec) {
  const theme = colors35(spec);
  const items = firstList(spec, ["items", "takeaways"], ["Context", "Evidence", "Decision"]).slice(0, 6);
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 760, titleSize: 42 }),
    box({ width: 724, flexDirection: "column" }, numberedRows(items, theme, { max: 6 })),
    box({ position: "absolute", right: 56, top: 126, width: 112, height: 310, backgroundColor: theme.primary, opacity: 0.12 })
  ]);
}
function timelineSteps(spec) {
  const theme = colors35(spec);
  const events = firstList(spec, ["events", "steps", "items"], ["Discover", "Design", "Deliver", "Measure"]).slice(0, 5);
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 760, titleSize: 40 }),
    box({ position: "absolute", left: 110, top: 330, width: 740, height: 4, backgroundColor: theme.primary, opacity: 0.55 }),
    box(
      { position: "absolute", left: 96, top: 254, flexDirection: "row", gap: 22 },
      events.map(
        (event, index) => box({ width: 130, flexDirection: "column", alignItems: "center" }, [
          TextBlock(String(index + 1).padStart(2, "0"), {
            width: 52,
            height: 52,
            color: theme.text,
            backgroundColor: index % 2 ? theme.accent : theme.primary,
            fontSize: 20,
            fontWeight: 850,
            padding: "14px 0",
            textAlign: "center",
            marginBottom: 18
          }),
          TextBlock(event, { color: theme.text, fontSize: 18, fontWeight: 700, textAlign: "center", lineHeight: 1.18 })
        ])
      )
    )
  ]);
}
function processFlow(spec) {
  const theme = colors35(spec);
  const steps = firstList(spec, ["steps", "items"], ["Input", "Normalize", "Render", "Verify"]).slice(0, 5);
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 730, titleSize: 40 }),
    box(
      { flexDirection: "row", gap: 18, marginTop: 26 },
      steps.map(
        (step, index) => box({ width: 154, height: 172, flexDirection: "column", backgroundColor: theme.panel, padding: 18 }, [
          TextBlock(String(index + 1), { color: theme.primary, fontSize: 28, fontWeight: 900, marginBottom: 20 }),
          TextBlock(step, { color: theme.text, fontSize: 21, fontWeight: 750, lineHeight: 1.15 }),
          box({ width: 48, height: 5, backgroundColor: index % 2 ? theme.accent : theme.primary, marginTop: "auto" })
        ])
      )
    ),
    TextBlock(text35(spec, "conclusion", ""), {
      position: "absolute",
      left: 74,
      bottom: 50,
      width: 812,
      minHeight: 48,
      color: theme.text,
      backgroundColor: theme.primary,
      opacity: 0.18,
      fontSize: 20,
      fontWeight: 750,
      padding: 14
    })
  ]);
}
function metricDashboard(spec) {
  const theme = colors35(spec);
  const metrics = firstList(spec, ["metrics", "items"], ["Velocity +32%", "Cost -18%", "Quality 96%", "Reach 4.2x"]).slice(0, 6);
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 710, titleSize: 38 }),
    box(
      { flexDirection: "row", flexWrap: "wrap", gap: 18, marginTop: 6 },
      metrics.map((metric, index) => smallCard(`METRIC ${index + 1}`, metric, theme))
    )
  ]);
}
function quoteFocus(spec) {
  const theme = colors35(spec);
  return pageShell(spec, [
    TextBlock("\u201C", { position: "absolute", left: 60, top: 36, color: theme.primary, fontSize: 132, fontWeight: 900, opacity: 0.7 }),
    TextBlock(text35(spec, "quote", text35(spec, "title", "A strong point belongs on a quiet page.")), {
      width: 720,
      marginTop: 116,
      marginLeft: 72,
      color: theme.text,
      fontSize: 42,
      fontWeight: 850,
      lineHeight: 1.13
    }),
    TextBlock(text35(spec, "attribution", ""), {
      marginLeft: 76,
      marginTop: 34,
      color: theme.muted,
      fontSize: 22,
      fontWeight: 700
    }),
    box({ position: "absolute", right: 80, bottom: 72, width: 150, height: 10, backgroundColor: theme.accent })
  ]);
}
function imageFeature(spec) {
  const theme = colors35(spec);
  const points = firstList(spec, ["points", "items"], ["Primary visual anchor", "Caption explains evidence", "Text stays out of the image"]).slice(0, 3);
  return pageShell(spec, [
    box({ position: "absolute", left: 56, top: 56, width: 452, height: 428, backgroundColor: theme.panel }),
    box({ position: "absolute", left: 86, top: 86, width: 392, height: 268, backgroundColor: theme.primary, opacity: 0.18 }),
    TextBlock(text35(spec, "image_label", "IMAGE"), { position: "absolute", left: 226, top: 204, color: theme.primary, fontSize: 28, fontWeight: 900 }),
    TextBlock(text35(spec, "caption", ""), { position: "absolute", left: 86, top: 386, width: 388, color: theme.muted, fontSize: 19, fontWeight: 650 }),
    box({ position: "absolute", left: 548, top: 72, width: 330 }, [pageHeader(spec, { titleWidth: 330, titleSize: 38 })]),
    box({ position: "absolute", left: 552, top: 280, width: 324, flexDirection: "column" }, numberedRows(points, theme, { max: 3 }))
  ]);
}
function researchPoster(spec) {
  const theme = colors35(spec);
  const sections = firstList(spec, ["sections", "items"], ["Context", "Method", "Result", "Implication"]).slice(0, 6);
  return pageShell(spec, [
    box({ position: "absolute", left: 56, top: 42, width: 588 }, [pageHeader(spec, { titleWidth: 588, titleSize: 34, subtitleKey: "authors" })]),
    box({ position: "absolute", right: 70, top: 54, width: 140, height: 96, backgroundColor: theme.primary, opacity: 0.18 }),
    box(
      { position: "absolute", left: 58, top: 194, flexDirection: "row", gap: 20 },
      [0, 1, 2].map(
        (column) => box(
          { width: 268, flexDirection: "column", gap: 14 },
          sections.slice(column * 2, column * 2 + 2).map(
            (section, index) => box({ height: 120, flexDirection: "column", backgroundColor: theme.panel, padding: 16 }, [
              TextBlock(section, { color: theme.primary, fontSize: 20, fontWeight: 850, marginBottom: 12 }),
              TextBlock(column === 1 && index === 0 ? text35(spec, "key_visual", "key visual") : "Evidence block", {
                color: theme.muted,
                fontSize: 17,
                fontWeight: 600
              })
            ])
          )
        )
      )
    )
  ]);
}
function dataStory(spec) {
  const theme = colors35(spec);
  const metrics = firstList(spec, ["metrics", "items"], ["North 42", "South 35", "West 28", "East 19"]).slice(0, 4);
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 600, titleSize: 38 }),
    box({ position: "absolute", left: 86, top: 260, flexDirection: "row", alignItems: "flex-end", gap: 34 }, metrics.map(
      (metric, index) => box({ width: 112, flexDirection: "column", alignItems: "center" }, [
        box({ width: 64, height: 82 + index * 28, backgroundColor: index % 2 ? theme.accent : theme.primary, marginBottom: 18 }),
        TextBlock(metric, { color: theme.text, fontSize: 18, fontWeight: 750, textAlign: "center" })
      ])
    )),
    TextBlock(text35(spec, "callout", ""), { position: "absolute", right: 72, top: 184, width: 260, color: theme.text, backgroundColor: theme.panel, fontSize: 24, fontWeight: 850, lineHeight: 1.14, padding: 22 })
  ]);
}
function riskAlert(spec) {
  const theme = colors35(spec);
  const risks = firstList(spec, ["risks", "items"], ["Scope drift", "Dependency delay", "Insufficient evidence"]).slice(0, 4);
  return pageShell(spec, [
    TextBlock(text35(spec, "severity", "L2"), { position: "absolute", right: 70, top: 54, color: theme.text, backgroundColor: theme.primary, fontSize: 28, fontWeight: 900, padding: "14px 22px" }),
    pageHeader(spec, { titleWidth: 690, titleSize: 40 }),
    box({ width: 800, flexDirection: "column", marginTop: 16 }, risks.map(
      (risk, index) => box({ height: 58, flexDirection: "row", alignItems: "center", backgroundColor: theme.panel, marginBottom: 14, padding: 16 }, [
        box({ width: 12, height: 34, backgroundColor: index === 0 ? theme.accent : theme.primary, marginRight: 16 }),
        TextBlock(risk, { color: theme.text, fontSize: 22, fontWeight: 760 })
      ])
    )),
    TextBlock(text35(spec, "summary", ""), { color: theme.muted, fontSize: 18, fontWeight: 650, marginTop: 6 })
  ]);
}
function roadmapLanes(spec) {
  const theme = colors35(spec);
  const lanes = firstList(spec, ["lanes", "items"], ["Now", "Next", "Later"]).slice(0, 4);
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 700, titleSize: 38 }),
    box({ flexDirection: "column", gap: 16, marginTop: 16 }, lanes.map(
      (lane, index) => box({ width: 820, height: 62, flexDirection: "row", alignItems: "center", backgroundColor: theme.panel, padding: "0 18px" }, [
        TextBlock(lane, { width: 132, color: theme.primary, fontSize: 21, fontWeight: 850 }),
        box({ flex: 1, height: 12, backgroundColor: index % 2 ? theme.accent : theme.primary, opacity: 0.38 }),
        TextBlock(`Q${index + 1}`, { width: 54, color: theme.text, fontSize: 18, fontWeight: 800, textAlign: "right" })
      ])
    ))
  ]);
}
function architectureBlueprint(spec) {
  const theme = colors35(spec);
  const nodes = firstList(spec, ["nodes", "items"], ["Planner", "CanvasSpec", "Renderer", "SVGlide"]).slice(0, 6);
  return pageShell(spec, [
    pageHeader(spec, { titleWidth: 630, titleSize: 36 }),
    box(
      { position: "absolute", left: 86, top: 240, flexDirection: "row", flexWrap: "wrap", gap: 24, width: 780 },
      nodes.map(
        (item, index) => box({ width: 236, height: 72, backgroundColor: theme.panel, borderWidth: 2, borderColor: index % 2 ? theme.accent : theme.primary, padding: 16 }, [
          TextBlock(item, { color: theme.text, fontSize: 20, fontWeight: 800 })
        ])
      )
    )
  ]);
}
function densePanelGrid(spec) {
  const theme = colors35(spec);
  const metrics = firstList(spec, ["metrics", "items"], ["Coverage 92", "Latency -18%", "Risk L2", "Quality 4.6"]).slice(0, 6);
  const notes = firstList(spec, ["notes", "sections"], ["Signal held across cohorts", "Bottleneck moved to onboarding", "Next wave needs owner clarity"]).slice(0, 3);
  return pageShell(spec, [
    box({ position: "absolute", left: 56, top: 48, width: 848, height: 444, borderWidth: 3, borderColor: theme.text }),
    box({ position: "absolute", left: 70, top: 62, width: 132, height: 88, backgroundColor: theme.panel, borderWidth: 2, borderColor: theme.primary }),
    TextBlock(text35(spec, "eyebrow", "GRID REPORT").toUpperCase(), {
      position: "absolute",
      left: 84,
      top: 88,
      width: 104,
      color: theme.text,
      fontSize: 17,
      fontWeight: 900,
      lineHeight: 1.1
    }),
    Title(text35(spec, "title", "Dense Signal Grid"), {
      position: "absolute",
      left: 226,
      top: 66,
      width: 620,
      color: theme.text,
      fontSize: 42,
      fontWeight: 900,
      lineHeight: 1.02
    }),
    TextBlock(text35(spec, "subtitle", ""), {
      position: "absolute",
      left: 226,
      top: 158,
      width: 560,
      color: theme.muted,
      fontSize: 19,
      fontWeight: 700,
      lineHeight: 1.22
    }),
    box(
      { position: "absolute", left: 70, top: 228, width: 548, flexDirection: "row", flexWrap: "wrap", gap: 12 },
      metrics.map(
        (metric, index) => box({ width: 170, height: 82, flexDirection: "column", backgroundColor: theme.panel, borderWidth: index % 3 === 0 ? 2 : 0, borderColor: theme.primary, padding: 14 }, [
          TextBlock(String(index + 1).padStart(2, "0"), { color: theme.primary, fontSize: 14, fontWeight: 850, marginBottom: 8 }),
          TextBlock(metric, { color: theme.text, fontSize: 19, fontWeight: 900, lineHeight: 1.08 })
        ])
      )
    ),
    box(
      { position: "absolute", right: 70, top: 230, width: 252, flexDirection: "column", gap: 12 },
      notes.map(
        (note2) => box({ minHeight: 76, backgroundColor: theme.panel, borderWidth: 2, borderColor: theme.primary, padding: 14 }, [
          TextBlock(note2, { color: theme.text, fontSize: 18, fontWeight: 900, lineHeight: 1.12 })
        ])
      )
    )
  ]);
}
function editorialQuoteChart(spec) {
  const theme = colors35(spec);
  const points = firstList(spec, ["points", "items"], ["Signal was visible before the metric moved", "The constraint is organizational, not technical", "Next action must be explicit"]).slice(0, 3);
  return pageShell(spec, [
    box({ position: "absolute", left: 54, top: 48, width: 852, height: 72, borderBottomWidth: 2, borderBottomColor: theme.primary }),
    TextBlock(text35(spec, "eyebrow", "EDITORIAL").toUpperCase(), { position: "absolute", left: 60, top: 72, color: theme.primary, fontSize: 16, fontWeight: 850 }),
    TextBlock(text35(spec, "section", "FIELD NOTE"), { position: "absolute", right: 62, top: 72, color: theme.muted, fontSize: 16, fontWeight: 750 }),
    TextBlock("\u201C", { position: "absolute", left: 58, top: 142, color: theme.primary, fontSize: 108, fontWeight: 900, lineHeight: 0.8 }),
    Title(text35(spec, "quote", text35(spec, "title", "The operating model changed before the dashboard caught up.")), {
      position: "absolute",
      left: 132,
      top: 148,
      width: 518,
      color: theme.text,
      fontSize: 43,
      fontWeight: 900,
      lineHeight: 1.04
    }),
    TextBlock(text35(spec, "attribution", ""), { position: "absolute", left: 138, top: 352, width: 420, color: theme.muted, fontSize: 18, fontWeight: 750 }),
    box(
      { position: "absolute", right: 70, top: 154, width: 212, flexDirection: "column", gap: 14 },
      points.map(
        (point, index) => box({ minHeight: 78, flexDirection: "row", backgroundColor: theme.panel, borderWidth: index === 0 ? 2 : 0, borderColor: theme.primary, padding: 14 }, [
          TextBlock(String(index + 1), { width: 32, color: theme.primary, fontSize: 26, fontWeight: 900 }),
          TextBlock(point, { flex: 1, color: theme.text, fontSize: 17, fontWeight: 760, lineHeight: 1.12 })
        ])
      )
    )
  ]);
}
function ledgerBriefing(spec) {
  const theme = colors35(spec);
  const items = firstList(spec, ["items", "takeaways"], ["Scope closed", "Evidence reviewed", "Decision pending", "Owner named"]).slice(0, 5);
  const metrics = firstList(spec, ["metrics", "stats"], ["Q2", "18%", "04"]).slice(0, 3);
  return pageShell(spec, [
    box({ position: "absolute", left: 56, top: 46, width: 848, height: 1, backgroundColor: theme.text }),
    box({ position: "absolute", left: 56, bottom: 46, width: 848, height: 1, backgroundColor: theme.text }),
    TextBlock(text35(spec, "eyebrow", "LEDGER").toUpperCase(), { position: "absolute", left: 58, top: 70, color: theme.muted, fontSize: 15, fontWeight: 800 }),
    Title(text35(spec, "title", "Operating Ledger"), {
      position: "absolute",
      left: 56,
      top: 104,
      width: 520,
      color: theme.text,
      fontSize: 54,
      fontWeight: 300,
      lineHeight: 1.02
    }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 58, top: 230, width: 492, color: theme.muted, fontSize: 20, lineHeight: 1.35 }),
    box({ position: "absolute", right: 62, top: 84, width: 250, flexDirection: "row", gap: 18 }, metrics.map(
      (metric) => box({ width: 70, flexDirection: "column", borderTopWidth: 1, borderTopColor: theme.text, paddingTop: 12 }, [
        TextBlock(metric, { color: theme.text, fontSize: 34, fontWeight: 300, lineHeight: 1 }),
        TextBlock("FIELD", { color: theme.muted, fontSize: 11, fontWeight: 800, marginTop: 8 })
      ])
    )),
    box({ position: "absolute", right: 64, top: 222, width: 326, flexDirection: "column" }, items.map(
      (item, index) => box({ height: 48, flexDirection: "row", alignItems: "center", borderTopWidth: 1, borderTopColor: theme.muted }, [
        TextBlock(String(index + 1).padStart(2, "0"), { width: 48, color: theme.muted, fontSize: 15, fontWeight: 800 }),
        TextBlock(item, { flex: 1, color: theme.text, fontSize: 18, fontWeight: 450, lineHeight: 1.18 })
      ])
    ))
  ]);
}
function intelligenceBrief(spec) {
  const theme = colors35(spec);
  const points = firstList(spec, ["points", "signals", "items"], ["Early signal", "Structural constraint", "Recommended action"]).slice(0, 4);
  return pageShell(spec, [
    box({ position: "absolute", left: 56, top: 56, width: 848, height: 52, borderBottomWidth: 1, borderBottomColor: theme.accent }),
    TextBlock(text35(spec, "eyebrow", "PRIVATE BRIEF").toUpperCase(), { position: "absolute", left: 62, top: 72, color: theme.accent, fontSize: 15, fontWeight: 850 }),
    TextBlock(text35(spec, "date", "CONFIDENTIAL"), { position: "absolute", right: 62, top: 72, color: theme.muted, fontSize: 15, fontWeight: 750 }),
    Title(text35(spec, "title", "Signal Briefing"), { position: "absolute", left: 70, top: 148, width: 602, color: theme.text, fontSize: 52, fontWeight: 700, lineHeight: 1.02 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 72, top: 282, width: 536, color: theme.muted, fontSize: 20, lineHeight: 1.32 }),
    box({ position: "absolute", right: 72, top: 150, width: 238, flexDirection: "column", gap: 14 }, points.map(
      (point, index) => box({ minHeight: 66, flexDirection: "column", borderLeftWidth: 3, borderLeftColor: index === 0 ? theme.accent : theme.panel, paddingLeft: 14 }, [
        TextBlock(`S${index + 1}`, { color: theme.accent, fontSize: 14, fontWeight: 850, marginBottom: 8 }),
        TextBlock(point, { color: theme.text, fontSize: 18, fontWeight: 650, lineHeight: 1.14 })
      ])
    )),
    box({ position: "absolute", left: 72, bottom: 70, width: 720, height: 1, backgroundColor: theme.accent, opacity: 0.7 })
  ]);
}
function printedProgram(spec) {
  const theme = colors35(spec);
  const items = firstList(spec, ["items", "courses", "agenda"], ["Opening note", "Main course", "Decision round", "Closing"]).slice(0, 5);
  return pageShell(spec, [
    box({ position: "absolute", left: 58, top: 50, width: 844, height: 438, borderWidth: 2, borderColor: theme.primary }),
    TextBlock(text35(spec, "edition", "EDITION 01"), { position: "absolute", left: 84, top: 80, color: theme.primary, fontSize: 17, fontWeight: 900 }),
    Title(text35(spec, "title", "Long Table Review").toUpperCase(), { position: "absolute", left: 82, top: 120, width: 514, color: theme.primary, fontSize: 54, fontWeight: 900, lineHeight: 0.92 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 86, top: 288, width: 430, color: theme.text, fontSize: 20, lineHeight: 1.35 }),
    box({ position: "absolute", right: 82, top: 88, width: 292, flexDirection: "column" }, items.map(
      (item, index) => box({ minHeight: 66, borderBottomWidth: 1, borderBottomColor: theme.primary, padding: "10px 0", flexDirection: "row" }, [
        TextBlock(String(index + 1).padStart(2, "0"), { width: 42, color: theme.primary, fontSize: 24, fontWeight: 800 }),
        TextBlock(item.toUpperCase(), { flex: 1, color: theme.primary, fontSize: 20, fontWeight: 850, lineHeight: 1.05 })
      ])
    )),
    TextBlock(text35(spec, "footer", "SVGlide program note"), { position: "absolute", left: 86, bottom: 76, color: theme.muted, fontSize: 16, fontWeight: 700 })
  ]);
}
function retroUiDashboard(spec) {
  const theme = colors35(spec);
  const panels = firstList(spec, ["panels", "items"], ["Build status: OK", "Open issues: 12", "Owner: Platform"]).slice(0, 4);
  return box({ width: CANVAS.width, height: CANVAS.height, position: "relative", flexDirection: "column", backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 48 }, [
    box({ position: "absolute", left: 70, top: 62, width: 820, height: 416, backgroundColor: theme.panel, borderWidth: 3, borderColor: theme.text }),
    box({ position: "absolute", left: 76, top: 68, width: 808, height: 38, backgroundColor: theme.primary, flexDirection: "row", alignItems: "center", padding: "0 12px" }, [
      TextBlock(text35(spec, "window_title", "SVGLIDE.EXE"), { color: theme.accent, fontSize: 18, fontWeight: 850 })
    ]),
    Title(text35(spec, "title", "Release Control Panel"), { position: "absolute", left: 96, top: 132, width: 500, color: theme.text, fontSize: 38, fontWeight: 800, lineHeight: 1.08 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 98, top: 228, width: 428, color: theme.muted, fontSize: 19, lineHeight: 1.28 }),
    box({ position: "absolute", right: 98, top: 132, width: 292, flexDirection: "column", gap: 12 }, panels.map(
      (panel) => box({ height: 62, backgroundColor: theme.background, borderWidth: 2, borderColor: theme.text, padding: 14 }, [
        TextBlock(panel, { color: theme.text, fontSize: 18, fontWeight: 750 })
      ])
    )),
    box({ position: "absolute", left: 96, bottom: 88, width: 768, height: 28, backgroundColor: theme.background, borderWidth: 2, borderColor: theme.text }, [
      TextBlock(text35(spec, "status", "READY"), { color: theme.primary, fontSize: 15, fontWeight: 900, padding: "5px 10px" })
    ])
  ]);
}
function productRibbon(spec) {
  const theme = colors35(spec);
  const cards = firstList(spec, ["cards", "items"], ["Feature A", "Feature B", "Feature C"]).slice(0, 4);
  const stripeColors = [theme.primary, theme.accent, theme.panel, theme.muted];
  const labelColors = [theme.primary, theme.accent, theme.text, theme.primary];
  return pageShell(spec, [
    box({ position: "absolute", left: 0, top: 0, width: CANVAS.width, height: 28, flexDirection: "row" }, stripeColors.map(
      (color) => box({ width: 240, height: 28, backgroundColor: color })
    )),
    TextBlock(text35(spec, "eyebrow", "CATALOG").toUpperCase(), { position: "absolute", left: 64, top: 70, color: theme.primary, fontSize: 16, fontWeight: 900 }),
    Title(text35(spec, "title", "Product Catalog"), { position: "absolute", left: 62, top: 102, width: 610, color: theme.text, fontSize: 58, fontWeight: 900, lineHeight: 0.92 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 66, top: 238, width: 470, color: theme.muted, fontSize: 20, lineHeight: 1.28 }),
    box({ position: "absolute", left: 64, bottom: 62, flexDirection: "row", gap: 16 }, cards.map(
      (card2, index) => box({ width: 194, height: 118, backgroundColor: index % 2 ? theme.panel : theme.background, borderWidth: 2, borderColor: theme.text, padding: 14 }, [
        TextBlock(String(index + 1).padStart(2, "0"), { color: labelColors[index % labelColors.length], fontSize: 24, fontWeight: 900, marginBottom: 12 }),
        TextBlock(card2, { color: theme.text, fontSize: 18, fontWeight: 850, lineHeight: 1.08 })
      ])
    )),
    box({ position: "absolute", right: 78, top: 94, width: 112, height: 112, borderRadius: 56, backgroundColor: theme.panel, borderWidth: 2, borderColor: theme.accent, alignItems: "center", justifyContent: "center" }, [
      TextBlock(text35(spec, "seal", "NEW"), { color: theme.text, fontSize: 25, fontWeight: 900 })
    ])
  ]);
}
function typeMassPoster(spec) {
  const theme = colors35(spec);
  const notes = firstList(spec, ["notes", "items"], ["One message", "No decoration", "High contrast"]).slice(0, 3);
  return box({ width: CANVAS.width, height: CANVAS.height, position: "relative", flexDirection: "column", backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 52 }, [
    box({ position: "absolute", left: 52, top: 48, width: 856, height: 1, backgroundColor: theme.primary, opacity: 0.62 }),
    TextBlock(text35(spec, "eyebrow", "STUDIO").toUpperCase(), { position: "absolute", left: 58, top: 66, color: theme.primary, fontSize: 15, fontWeight: 850 }),
    TextBlock(text35(spec, "counter", "01/06"), { position: "absolute", right: 58, top: 66, color: theme.primary, fontSize: 15, fontWeight: 850 }),
    Title(text35(spec, "title", "MAKE IT LOUD").toUpperCase(), { position: "absolute", left: 58, top: 118, width: 800, color: theme.primary, fontSize: 82, fontWeight: 900, lineHeight: 0.88 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 62, bottom: 120, width: 520, color: theme.muted, fontSize: 21, lineHeight: 1.25 }),
    box({ position: "absolute", right: 70, bottom: 78, width: 248, flexDirection: "column" }, notes.map(
      (note2) => box({ borderTopWidth: 2, borderTopColor: theme.primary, padding: "12px 0" }, [
        TextBlock(note2.toUpperCase(), { color: theme.primary, fontSize: 18, fontWeight: 900, lineHeight: 1.05 })
      ])
    ))
  ]);
}
function brutalistMatrix(spec) {
  const theme = colors35(spec);
  const cells = firstList(spec, ["cells", "items"], ["Price clarity", "Time to value", "Risk level", "Owner fit", "Migration cost", "Evidence depth"]).slice(0, 6);
  return box({ width: CANVAS.width, height: CANVAS.height, position: "relative", flexDirection: "column", backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 50 }, [
    box({ position: "absolute", left: 50, top: 50, width: 860, height: 440, borderWidth: 3, borderColor: theme.text }),
    TextBlock(text35(spec, "eyebrow", "MATRIX").toUpperCase(), { position: "absolute", left: 70, top: 74, color: theme.text, fontSize: 15, fontWeight: 900 }),
    Title(text35(spec, "title", "Decision Matrix").toUpperCase(), { position: "absolute", left: 70, top: 104, width: 492, color: theme.text, fontSize: 50, fontWeight: 900, lineHeight: 0.96 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 70, top: 222, width: 426, color: theme.muted, fontSize: 19, lineHeight: 1.22 }),
    box({ position: "absolute", right: 72, top: 76, width: 314, height: 92, backgroundColor: theme.panel, borderWidth: 3, borderColor: theme.primary, padding: 14 }, [
      TextBlock(text35(spec, "callout", "BEST OPTION").toUpperCase(), { color: theme.text, fontSize: 24, fontWeight: 900, lineHeight: 1 })
    ]),
    box({ position: "absolute", left: 70, bottom: 76, width: 820, flexDirection: "row", flexWrap: "wrap" }, cells.map(
      (cell, index) => box({ width: 273, height: 74, borderWidth: 2, borderColor: theme.text, backgroundColor: index % 2 ? theme.panel : theme.background, padding: 12, flexDirection: "row" }, [
        TextBlock(String(index + 1), { width: 34, color: theme.primary, fontSize: 28, fontWeight: 900 }),
        TextBlock(cell, { flex: 1, color: theme.text, fontSize: 18, fontWeight: 850, lineHeight: 1.08 })
      ])
    ))
  ]);
}
function annotatedFieldBoard(spec) {
  const theme = colors35(spec);
  const notes = firstList(spec, ["notes", "items"], ["Interview signal", "Evidence needs follow-up", "Decision owner named"]).slice(0, 4);
  return pageShell(spec, [
    box({ position: "absolute", left: 62, top: 56, width: 836, height: 428, borderWidth: 2, borderColor: theme.muted, backgroundColor: theme.panel }),
    TextBlock(text35(spec, "eyebrow", "FIELD BOARD").toUpperCase(), { position: "absolute", left: 86, top: 84, color: theme.primary, fontSize: 16, fontWeight: 900 }),
    Title(text35(spec, "title", "Annotated Evidence"), { position: "absolute", left: 86, top: 116, width: 520, color: theme.text, fontSize: 48, fontWeight: 850, lineHeight: 1.02 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 88, top: 228, width: 430, color: theme.muted, fontSize: 20, lineHeight: 1.28 }),
    TextBlock(text35(spec, "stamp", "REVIEWED").toUpperCase(), { position: "absolute", right: 90, top: 86, color: theme.primary, borderWidth: 3, borderColor: theme.primary, fontSize: 22, fontWeight: 900, padding: "10px 14px" }),
    box({ position: "absolute", right: 86, top: 160, width: 302, flexDirection: "column", gap: 14 }, notes.map(
      (note2, index) => box({ minHeight: 66, backgroundColor: theme.background, borderWidth: 2, borderColor: theme.text, padding: 14 }, [
        TextBlock(`NOTE ${index + 1}`, { color: theme.primary, fontSize: 13, fontWeight: 900, marginBottom: 8 }),
        TextBlock(note2, { color: theme.text, fontSize: 18, fontWeight: 750, lineHeight: 1.12 })
      ])
    )),
    box({ position: "absolute", left: 86, bottom: 82, width: 430, flexDirection: "row", gap: 12 }, firstList(spec, ["tags"], ["USER", "EVIDENCE", "NEXT"]).slice(0, 3).map(
      (tag) => TextBlock(tag.toUpperCase(), { color: theme.text, backgroundColor: theme.panel, fontSize: 14, fontWeight: 900, padding: "8px 12px" })
    ))
  ]);
}
function architecturalSpec(spec) {
  const theme = colors35(spec);
  const rows = firstList(spec, ["rows", "items"], ["Foundation", "Structure", "Interface", "Handoff"]).slice(0, 4);
  return pageShell(spec, [
    box({ position: "absolute", left: 70, top: 62, width: 820, height: 414, borderWidth: 1, borderColor: theme.muted }),
    box({ position: "absolute", left: 92, top: 86, width: 258, height: 258, borderWidth: 2, borderColor: theme.primary }),
    box({ position: "absolute", left: 142, top: 136, width: 158, height: 158, borderRadius: 79, borderWidth: 2, borderColor: theme.accent }),
    TextBlock(text35(spec, "eyebrow", "SPEC").toUpperCase(), { position: "absolute", left: 392, top: 90, color: theme.muted, fontSize: 15, fontWeight: 850 }),
    Title(text35(spec, "title", "Architecture Spec"), { position: "absolute", left: 390, top: 124, width: 430, color: theme.text, fontSize: 46, fontWeight: 650, lineHeight: 1.03 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 392, top: 238, width: 396, color: theme.muted, fontSize: 20, lineHeight: 1.32 }),
    box({ position: "absolute", left: 92, bottom: 84, width: 746, flexDirection: "row", gap: 14 }, rows.map(
      (row2, index) => box({ width: 176, height: 70, borderTopWidth: 1, borderTopColor: theme.primary, paddingTop: 12 }, [
        TextBlock(String(index + 1).padStart(2, "0"), { color: theme.primary, fontSize: 16, fontWeight: 850, marginBottom: 8 }),
        TextBlock(row2, { color: theme.text, fontSize: 18, fontWeight: 700, lineHeight: 1.1 })
      ])
    ))
  ]);
}
function trendGridReport(spec) {
  const theme = colors35(spec);
  const trends = firstList(spec, ["trends", "items"], ["Model cost pressure", "Agent workflows", "Design ops maturity", "Governance gaps"]).slice(0, 4);
  return pageShell(spec, [
    box({ position: "absolute", left: 52, top: 52, width: 856, height: 436, borderWidth: 2, borderColor: theme.primary, opacity: 0.9 }),
    TextBlock(text35(spec, "eyebrow", "TREND INDEX").toUpperCase(), { position: "absolute", left: 72, top: 74, color: theme.primary, fontSize: 15, fontWeight: 900 }),
    Title(text35(spec, "title", "Cobalt Trend Report"), { position: "absolute", left: 70, top: 112, width: 570, color: theme.primary, fontSize: 58, fontWeight: 500, lineHeight: 0.94 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 72, top: 250, width: 500, color: theme.muted, fontSize: 19, lineHeight: 1.3 }),
    box({ position: "absolute", right: 74, top: 92, width: 170, height: 170, flexDirection: "row", flexWrap: "wrap" }, Array.from({ length: 16 }).map(
      (_, index) => box({ width: 34, height: 34, backgroundColor: index % 3 === 0 ? theme.primary : theme.panel, marginRight: 4, marginBottom: 4, opacity: index % 3 === 0 ? 1 : 0.42 })
    )),
    box({ position: "absolute", left: 72, bottom: 74, width: 810, flexDirection: "column" }, trends.map(
      (trend, index) => box({ height: 42, flexDirection: "row", alignItems: "center", borderTopWidth: 1, borderTopColor: theme.primary }, [
        TextBlock(`0${index + 1}`, { width: 54, color: theme.primary, fontSize: 16, fontWeight: 850 }),
        TextBlock(trend, { flex: 1, color: theme.text, fontSize: 19, fontWeight: 650 }),
        TextBlock(index % 2 ? "RISING" : "WATCH", { width: 94, color: theme.primary, fontSize: 13, fontWeight: 900, textAlign: "right" })
      ])
    ))
  ]);
}
function serifStatEditorial(spec) {
  const theme = colors35(spec);
  const cards = firstList(spec, ["cards", "items"], ["Quality held", "Narrative simplified", "Next evidence needed"]).slice(0, 3);
  return pageShell(spec, [
    TextBlock(text35(spec, "eyebrow", "EDITORIAL").toUpperCase(), { position: "absolute", left: 70, top: 72, color: theme.primary, fontSize: 16, fontWeight: 900 }),
    Title(text35(spec, "stat", "73%"), { position: "absolute", left: 68, top: 104, width: 360, color: theme.primary, fontSize: 118, fontWeight: 500, lineHeight: 0.9 }),
    Title(text35(spec, "title", "Evidence moved the decision"), { position: "absolute", left: 442, top: 104, width: 380, color: theme.text, fontSize: 44, fontWeight: 600, lineHeight: 1.02 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 444, top: 238, width: 360, color: theme.muted, fontSize: 20, lineHeight: 1.32 }),
    box({ position: "absolute", left: 70, bottom: 70, flexDirection: "row", gap: 18 }, cards.map(
      (card2, index) => box({ width: 252, minHeight: 112, borderTopWidth: 3, borderTopColor: index === 0 ? theme.accent : theme.primary, backgroundColor: theme.panel, padding: 16 }, [
        TextBlock(card2, { color: theme.text, fontSize: 22, fontWeight: 650, lineHeight: 1.12 })
      ])
    ))
  ]);
}
function posterStatPunch(spec) {
  const theme = colors35(spec);
  const pillars = firstList(spec, ["pillars", "items"], ["Bold claim", "Evidence block", "Next move"]).slice(0, 3);
  return box({ width: CANVAS.width, height: CANVAS.height, position: "relative", flexDirection: "column", backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 52 }, [
    box({ position: "absolute", left: 48, top: 48, width: 864, height: 444, borderWidth: 3, borderColor: theme.text }),
    TextBlock(text35(spec, "eyebrow", "POSTER").toUpperCase(), { position: "absolute", left: 72, top: 72, color: theme.text, fontSize: 16, fontWeight: 900 }),
    Title(text35(spec, "title", "Make the call").toUpperCase(), { position: "absolute", left: 70, top: 104, width: 610, color: theme.text, fontSize: 66, fontWeight: 900, lineHeight: 0.9 }),
    Title(text35(spec, "stat", "3X"), { position: "absolute", right: 82, top: 96, width: 184, color: theme.primary, fontSize: 118, fontWeight: 900, lineHeight: 0.86 }),
    TextBlock(text35(spec, "subtitle", ""), { position: "absolute", left: 74, top: 272, width: 470, color: theme.muted, fontSize: 20, lineHeight: 1.28 }),
    box({ position: "absolute", left: 74, bottom: 76, flexDirection: "row", gap: 16 }, pillars.map(
      (pillar, index) => box({ width: 250, minHeight: 86, borderTopWidth: 3, borderTopColor: theme.primary, paddingTop: 12 }, [
        TextBlock(`0${index + 1}`, { color: theme.primary, fontSize: 28, fontWeight: 900, marginBottom: 6 }),
        TextBlock(pillar, { color: theme.text, fontSize: 20, fontWeight: 850, lineHeight: 1.08 })
      ])
    ))
  ]);
}
var BEAUTIFUL_TEMPLATE_CONFIGS = {};
function firstConfiguredItems(spec, cfg, fallback = ["Signal", "Evidence", "Next move"]) {
  return firstList(spec, cfg.listKeys || ["items"], fallback);
}
function templateBadge(spec, cfg, style = {}) {
  const theme = colors35(spec);
  return TextBlock(text35(spec, "eyebrow", cfg.label).toUpperCase(), {
    color: theme.primary,
    fontSize: 15,
    fontWeight: 900,
    letterSpacing: 0,
    ...style
  });
}
function beautifulTemplate(spec, cfg) {
  const theme = colors35(spec);
  const items = firstConfiguredItems(spec, cfg).slice(0, 6);
  const title = text35(spec, "title", "Untitled");
  const subtitle = text35(spec, "subtitle", "");
  const quote = text35(spec, "quote", text35(spec, "lede", ""));
  const stat = text35(spec, "stat", items[0] || "");
  if (cfg.mode === "console") {
    return box({ width: CANVAS.width, height: CANVAS.height, position: "relative", backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 48 }, [
      box({ position: "absolute", left: 38, top: 34, width: 884, height: 472, borderWidth: 3, borderColor: theme.primary, backgroundColor: theme.panel }),
      box({ position: "absolute", left: 70, top: 70, width: 820, height: 34, flexDirection: "row", gap: 10 }, Array.from({ length: 18 }).map(
        (_, index) => box({ width: index % 4 === 0 ? 56 : 28, height: 10, backgroundColor: index % 3 === 0 ? theme.accent : theme.primary, opacity: index % 2 ? 0.42 : 0.78 })
      )),
      templateBadge(spec, cfg, { position: "absolute", left: 76, top: 122 }),
      Title(title, { position: "absolute", left: 74, top: 154, width: 548, color: theme.text, fontSize: 52, fontWeight: 900, lineHeight: 0.96 }),
      TextBlock(subtitle, { position: "absolute", left: 76, top: 278, width: 480, color: theme.muted, fontSize: 20, lineHeight: 1.24 }),
      box({ position: "absolute", right: 76, top: 130, width: 236, flexDirection: "column", gap: 12 }, items.slice(0, 4).map(
        (item, index) => box({ minHeight: 54, borderWidth: 2, borderColor: index % 2 ? theme.accent : theme.primary, backgroundColor: theme.background, padding: 12 }, [
          TextBlock(item, { color: theme.text, fontSize: 18, fontWeight: 800, lineHeight: 1.1 })
        ])
      )),
      TextBlock("PX", { position: "absolute", left: 76, bottom: 64, color: theme.accent, fontSize: 56, fontWeight: 900 })
    ]);
  }
  if (cfg.mode === "programme" || cfg.mode === "manual") {
    return pageShell(spec, [
      box({ position: "absolute", left: 58, top: 52, width: 844, height: 438, borderWidth: cfg.mode === "manual" ? 3 : 2, borderColor: theme.primary }),
      templateBadge(spec, cfg, { position: "absolute", left: 82, top: 78 }),
      Title(title, { position: "absolute", left: 80, top: 112, width: cfg.mode === "manual" ? 382 : 500, color: theme.text, fontSize: cfg.mode === "manual" ? 46 : 58, fontWeight: 850, lineHeight: 0.96 }),
      TextBlock(subtitle, { position: "absolute", left: 82, top: cfg.mode === "manual" ? 232 : 254, width: 390, color: theme.muted, fontSize: 19, lineHeight: 1.28 }),
      box({ position: "absolute", right: 80, top: 84, width: 330, flexDirection: "column" }, items.slice(0, 5).map(
        (item, index) => box({ minHeight: 58, flexDirection: "row", alignItems: "center", borderTopWidth: 2, borderTopColor: theme.primary, padding: "10px 0" }, [
          TextBlock(String(index + 1).padStart(2, "0"), { width: 48, color: theme.accent, fontSize: 18, fontWeight: 900 }),
          TextBlock(item, { flex: 1, color: theme.text, fontSize: 19, fontWeight: 750, lineHeight: 1.12 })
        ])
      )),
      TextBlock(text35(spec, "footer", text35(spec, "venue", "")), { position: "absolute", left: 82, bottom: 78, width: 430, color: theme.primary, fontSize: 17, fontWeight: 850 })
    ]);
  }
  if (cfg.mode === "block-grid" || cfg.mode === "creative-grid" || cfg.mode === "capsule" || cfg.mode === "sticky") {
    const rounded = cfg.mode === "capsule" ? 999 : cfg.mode === "sticky" ? 2 : 0;
    const roundedStyle = rounded ? { borderRadius: rounded } : {};
    return pageShell(spec, [
      templateBadge(spec, cfg, { position: "absolute", left: 70, top: 66 }),
      Title(title, { position: "absolute", left: 68, top: 96, width: 520, color: theme.text, fontSize: 48, fontWeight: 900, lineHeight: 0.98 }),
      TextBlock(subtitle, { position: "absolute", left: 70, top: 210, width: 480, color: theme.muted, fontSize: 19, lineHeight: 1.28 }),
      box({ position: "absolute", right: 70, top: 70, width: 248, height: 138, backgroundColor: theme.accent, opacity: cfg.mode === "sticky" ? 0.36 : 0.92, ...roundedStyle }),
      box({ position: "absolute", left: 70, bottom: 66, width: 820, flexDirection: "row", flexWrap: "wrap", gap: 14 }, items.slice(0, 6).map(
        (item, index) => box({ width: cfg.mode === "sticky" ? 246 : 258, minHeight: cfg.mode === "capsule" ? 58 : 76, backgroundColor: index % 2 ? theme.surface : theme.panel, borderWidth: 2, borderColor: theme.primary, padding: 14, ...roundedStyle }, [
          TextBlock(item, { color: theme.text, fontSize: 18, fontWeight: 800, lineHeight: 1.1 })
        ])
      ))
    ]);
  }
  if (cfg.mode === "cover-editorial" || cfg.mode === "manifesto" || cfg.mode === "nocturne") {
    return box({ width: CANVAS.width, height: CANVAS.height, position: "relative", backgroundColor: theme.background, color: theme.text, fontFamily: DEFAULT_FONT_FAMILY, padding: 54 }, [
      templateBadge(spec, cfg, { position: "absolute", left: 76, top: 70, color: cfg.mode === "manifesto" ? theme.text : theme.primary }),
      Title(title.toUpperCase(), { position: "absolute", left: 74, top: 108, width: cfg.mode === "manifesto" ? 720 : 620, color: theme.text, fontSize: cfg.mode === "manifesto" ? 64 : 58, fontWeight: 900, lineHeight: 0.9 }),
      TextBlock(subtitle, { position: "absolute", left: 78, top: 276, width: 510, color: theme.muted, fontSize: 20, lineHeight: 1.25 }),
      box({ position: "absolute", right: 78, top: 86, width: 210, height: 210, borderWidth: 3, borderColor: theme.primary, backgroundColor: cfg.mode === "manifesto" ? theme.accent : theme.panel }),
      TextBlock(stat || cfg.label, { position: "absolute", right: 94, top: 142, width: 178, color: cfg.mode === "manifesto" ? theme.background : theme.primary, fontSize: 34, fontWeight: 900, lineHeight: 1, textAlign: "center" }),
      box({ position: "absolute", left: 78, bottom: 70, flexDirection: "row", gap: 14 }, items.slice(0, 3).map(
        (item, index) => box({ width: 250, minHeight: 82, borderTopWidth: 3, borderTopColor: index === 0 ? theme.accent : theme.primary, paddingTop: 12 }, [
          TextBlock(item, { color: theme.text, fontSize: 20, fontWeight: 820, lineHeight: 1.08 })
        ])
      ))
    ]);
  }
  if (cfg.mode === "organic" || cfg.mode === "midcentury" || cfg.mode === "playful") {
    return pageShell(spec, [
      box({ position: "absolute", left: 62, top: 58, width: 318, height: 424, backgroundColor: theme.panel }),
      box({ position: "absolute", left: 96, top: 92, width: 248, height: 154, backgroundColor: theme.surface, borderWidth: 2, borderColor: theme.primary }),
      templateBadge(spec, cfg, { position: "absolute", left: 418, top: 76 }),
      Title(title, { position: "absolute", left: 416, top: 112, width: 430, color: theme.text, fontSize: 46, fontWeight: 760, lineHeight: 1 }),
      TextBlock(subtitle, { position: "absolute", left: 418, top: 234, width: 386, color: theme.muted, fontSize: 19, lineHeight: 1.3 }),
      box({ position: "absolute", left: 416, bottom: 70, width: 410, flexDirection: "column", gap: 12 }, items.slice(0, 3).map(
        (item, index) => box({ minHeight: 52, flexDirection: "row", alignItems: "center" }, [
          box({ width: 18, height: 18, borderRadius: cfg.mode === "midcentury" ? 0 : 9, backgroundColor: index % 2 ? theme.accent : theme.primary, marginRight: 14 }),
          TextBlock(item, { flex: 1, color: theme.text, fontSize: 20, fontWeight: 750, lineHeight: 1.12 })
        ])
      ))
    ]);
  }
  if (cfg.mode === "zine" || cfg.mode === "soft-workshop") {
    return pageShell(spec, [
      box({ position: "absolute", left: 70, top: 62, width: 364, height: 416, backgroundColor: theme.panel, borderWidth: 2, borderColor: theme.primary }),
      box({ position: "absolute", left: 104, top: 94, width: 296, height: 120, backgroundColor: theme.surface }),
      templateBadge(spec, cfg, { position: "absolute", left: 470, top: 76 }),
      Title(title, { position: "absolute", left: 468, top: 112, width: 360, color: theme.text, fontSize: 44, fontWeight: 820, lineHeight: 1 }),
      TextBlock(quote || subtitle, { position: "absolute", left: 470, top: 244, width: 342, color: theme.muted, fontSize: 21, fontWeight: 650, lineHeight: 1.22 }),
      box({ position: "absolute", left: 470, bottom: 72, flexDirection: "row", gap: 12 }, items.slice(0, 3).map(
        (item) => box({ width: 112, minHeight: 92, backgroundColor: theme.surface, borderWidth: 2, borderColor: theme.primary, padding: 10 }, [
          TextBlock(item, { color: theme.text, fontSize: 16, fontWeight: 800, lineHeight: 1.1 })
        ])
      ))
    ]);
  }
  return pageShell(spec, [
    templateBadge(spec, cfg, { position: "absolute", left: 72, top: 70 }),
    Title(title, { position: "absolute", left: 70, top: 108, width: 600, color: theme.text, fontSize: cfg.mode === "scholar" ? 50 : 46, fontWeight: 780, lineHeight: 1.02 }),
    TextBlock(quote || subtitle, { position: "absolute", left: 72, top: 242, width: 560, color: theme.muted, fontSize: 21, lineHeight: 1.3 }),
    box({ position: "absolute", right: 76, top: 78, width: 170, height: 330, borderWidth: 2, borderColor: theme.primary, backgroundColor: theme.panel }),
    box({ position: "absolute", left: 72, bottom: 72, flexDirection: "row", gap: 16 }, items.slice(0, 3).map(
      (item, index) => box({ width: 244, minHeight: 86, borderTopWidth: 3, borderTopColor: index === 0 ? theme.accent : theme.primary, paddingTop: 12 }, [
        TextBlock(item, { color: theme.text, fontSize: 20, fontWeight: 740, lineHeight: 1.1 })
      ])
    ))
  ]);
}
function renderTree(spec) {
  if (spec.template_id === "cover-hero") return coverHero(spec);
  if (spec.template_id === "comparison-cards") return comparisonCards(spec);
  if (spec.template_id === "summary-final") return summaryFinal(spec);
  if (spec.template_id === "section-title") return sectionTitle(spec);
  if (spec.template_id === "agenda-list") return agendaList(spec);
  if (spec.template_id === "timeline-steps") return timelineSteps(spec);
  if (spec.template_id === "process-flow") return processFlow(spec);
  if (spec.template_id === "metric-dashboard") return metricDashboard(spec);
  if (spec.template_id === "quote-focus") return quoteFocus(spec);
  if (spec.template_id === "image-feature") return imageFeature(spec);
  if (spec.template_id === "research-poster") return researchPoster(spec);
  if (spec.template_id === "data-story") return dataStory(spec);
  if (spec.template_id === "risk-alert") return riskAlert(spec);
  if (spec.template_id === "roadmap-lanes") return roadmapLanes(spec);
  if (spec.template_id === "architecture-blueprint") return architectureBlueprint(spec);
  const beautifulTree = renderBeautifulTemplate(spec);
  if (beautifulTree) return beautifulTree;
  if (spec.template_id === "dense-panel-grid") return densePanelGrid(spec);
  if (spec.template_id === "editorial-quote-chart") return editorialQuoteChart(spec);
  if (spec.template_id === "ledger-briefing") return ledgerBriefing(spec);
  if (spec.template_id === "intelligence-brief") return intelligenceBrief(spec);
  if (spec.template_id === "printed-program") return printedProgram(spec);
  if (spec.template_id === "retro-ui-dashboard") return retroUiDashboard(spec);
  if (spec.template_id === "product-ribbon") return productRibbon(spec);
  if (spec.template_id === "type-mass-poster") return typeMassPoster(spec);
  if (spec.template_id === "brutalist-matrix") return brutalistMatrix(spec);
  if (spec.template_id === "annotated-field-board") return annotatedFieldBoard(spec);
  if (spec.template_id === "architectural-spec") return architecturalSpec(spec);
  if (spec.template_id === "trend-grid-report") return trendGridReport(spec);
  if (spec.template_id === "serif-stat-editorial") return serifStatEditorial(spec);
  if (spec.template_id === "poster-stat-punch") return posterStatPunch(spec);
  const debugFallbackConfig = BEAUTIFUL_TEMPLATE_CONFIGS[spec.template_id];
  if (debugFallbackConfig && (spec.selection_scope === "debug" || spec.selection_scope === "fixture" || spec.debug === true)) {
    return beautifulTemplate(spec, debugFallbackConfig);
  }
  throw new Error(`unsupported template_id for Satori adapter: ${spec.template_id}`);
}

// render.mjs
var SATORI_VERSION = "0.26.0";
var RESVG_VERSION = "2.6.2";
var DEFAULT_FONT_FAMILY2 = "SVGlideDefault";
var DEFAULT_FONT_CANDIDATES = [
  "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
  "/System/Library/Fonts/Supplemental/Arial.ttf",
  "/System/Library/Fonts/Supplemental/Verdana.ttf",
  "/System/Library/Fonts/Supplemental/Trebuchet MS.ttf",
  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
  "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
  "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
  "C:\\Windows\\Fonts\\arial.ttf"
];
async function pathExists(candidate) {
  try {
    await fs.access(candidate);
    return true;
  } catch {
    return false;
  }
}
async function resolveFontPath(candidates = DEFAULT_FONT_CANDIDATES) {
  if (process.env.SVGLIDE_SATORI_FONT_PATH) {
    return process.env.SVGLIDE_SATORI_FONT_PATH;
  }
  for (const candidate of candidates) {
    if (await pathExists(candidate)) {
      return candidate;
    }
  }
  for (const candidate of DEFAULT_FONT_CANDIDATES) {
    if (await pathExists(candidate)) {
      return candidate;
    }
  }
  throw new Error(
    "no usable Satori font found; set SVGLIDE_SATORI_FONT_PATH to a .ttf/.otf font available on this machine"
  );
}
async function readFontManifest() {
  const manifestUrl = new URL("./font-manifest.json", import.meta.url);
  return JSON.parse(await fs.readFile(manifestUrl, "utf8"));
}
async function loadFonts(spec = {}) {
  const manifest = await readFontManifest();
  const manifestRoles = manifest.roles || {};
  const themeRoles = fontRolesFromTheme(spec);
  const requestedRoles = fontRoleAliasesFromTheme(spec);
  const fonts = [];
  const seen = /* @__PURE__ */ new Set();
  const resolvedRoles = {};
  async function addFont({ family, weight = 400, style = "normal", candidates = DEFAULT_FONT_CANDIDATES, role = null, source = "manifest" }) {
    const fontPath = await resolveFontPath(candidates);
    const key = `${family}:${weight}:${style}:${fontPath}`;
    if (!seen.has(key)) {
      const data = await fs.readFile(fontPath);
      fonts.push({ name: family, data, weight, style, path: fontPath });
      seen.add(key);
    }
    if (role) {
      resolvedRoles[role] = { family, weight, style, path: fontPath, source };
    }
  }
  await addFont({ family: manifest.default_family || DEFAULT_FONT_FAMILY2, weight: 400, source: "default" });
  for (const role of REQUIRED_FONT_ROLES) {
    const manifestRole = manifestRoles[role] || {};
    const themeRole = themeRoles[role] || {};
    await addFont({
      family: themeRole.family || manifestRole.family || DEFAULT_FONT_FAMILY2,
      weight: typeof manifestRole.weight === "number" ? manifestRole.weight : 400,
      style: manifestRole.style || "normal",
      candidates: Array.isArray(manifestRole.candidates) ? manifestRole.candidates : DEFAULT_FONT_CANDIDATES,
      role,
      source: requestedRoles[role] ? "theme.typography.font_roles" : "manifest"
    });
  }
  return {
    fonts,
    primaryFont: fonts[0],
    receipt: {
      version: "svglide-artboard-font-receipt/v1",
      default_family: manifest.default_family || DEFAULT_FONT_FAMILY2,
      requested_roles: requestedRoles,
      resolved_roles: resolvedRoles,
      font_count: fonts.length,
      font_paths: Array.from(new Set(fonts.map((font) => font.path)))
    }
  };
}
async function loadSatori() {
  try {
    return (await import("satori")).default;
  } catch (error) {
    console.error("satori dependency is not available in this adapter runtime");
    console.error("development fix: run pnpm install --frozen-lockfile in skills/lark-slides/scripts/artboard_renderer");
    console.error("release fix: install satori as an external runtime dependency before running dist/render.mjs --check-runtime");
    console.error(String(error?.message || error));
    process.exit(3);
  }
}
async function loadResvg() {
  try {
    return (await import("@resvg/resvg-js")).Resvg;
  } catch (error) {
    console.error("@resvg/resvg-js native dependency is not available in this adapter runtime");
    console.error("fix: run pnpm --dir skills/lark-slides/scripts/artboard_renderer install --frozen-lockfile");
    console.error("release fix: install the platform-native @resvg/resvg-js package before running dist/render.mjs --check-runtime");
    console.error(String(error?.message || error));
    process.exit(4);
  }
}
async function checkRuntime() {
  await loadSatori();
  const Resvg = await loadResvg();
  const fontBundle = await loadFonts({});
  const probe = '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="#000"/></svg>';
  new Resvg(probe).render().asPng();
  console.log(JSON.stringify({ ok: true, renderer: "satori-resvg", satori_version: SATORI_VERSION, resvg_version: RESVG_VERSION, font_path: fontBundle.primaryFont.path, font_receipt: fontBundle.receipt }));
}
function serializeObservation(node2) {
  const props = node2?.props || {};
  const safeProps = {};
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith("data-") && ["string", "number", "boolean"].includes(typeof value)) {
      safeProps[key] = value;
    }
  }
  return {
    left: node2?.left,
    top: node2?.top,
    width: node2?.width,
    height: node2?.height,
    type: node2?.type,
    key: node2?.key,
    textContent: node2?.textContent,
    props: safeProps
  };
}
async function main() {
  const [, , inputPath, outputPath, pngPath, metadataPath, observationsPath] = process.argv;
  if (inputPath === "--check-runtime") {
    await checkRuntime();
    return;
  }
  if (!inputPath || !outputPath) {
    console.error("usage: node render.mjs <canvas-spec.json> <output.svg> [output.png] [metadata.json]");
    process.exit(2);
  }
  const satori = await loadSatori();
  const Resvg = await loadResvg();
  const spec = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const fontBundle = await loadFonts(spec);
  const typographyRoles = typographyRolesFromTheme(spec);
  const textStyleRoles = spec.theme?.typography?.text_style_roles || {};
  const observations = [];
  const svg = await satori(renderTree(spec), {
    width: 960,
    height: 540,
    embedFont: false,
    fonts: fontBundle.fonts,
    onNodeDetected: (node2) => {
      observations.push(serializeObservation(node2));
    }
  });
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(outputPath, svg);
  let pngBytes = null;
  if (pngPath) {
    pngBytes = new Resvg(svg, {
      fitTo: { mode: "width", value: 960 },
      font: { loadSystemFonts: true }
    }).render().asPng();
    await fs.mkdir(path.dirname(pngPath), { recursive: true });
    await fs.writeFile(pngPath, pngBytes);
  }
  if (metadataPath) {
    await fs.mkdir(path.dirname(metadataPath), { recursive: true });
    await fs.writeFile(
      metadataPath,
      JSON.stringify(
        {
          node_version: process.version,
          satori_version: SATORI_VERSION,
          resvg_version: RESVG_VERSION,
          font_path: fontBundle.primaryFont.path,
          font_paths: fontBundle.receipt.font_paths,
          font_receipt: fontBundle.receipt,
          font_roles: fontBundle.receipt.resolved_roles,
          typography_roles: typographyRoles,
          text_style_roles: textStyleRoles,
          typography_strategy_source: spec.theme?.typography?.strategy_source || null,
          png_bytes: pngBytes ? pngBytes.length : null
        },
        null,
        2
      ) + "\n"
    );
  }
  if (observationsPath) {
    await fs.mkdir(path.dirname(observationsPath), { recursive: true });
    await fs.writeFile(
      observationsPath,
      JSON.stringify(
        {
          version: "svglide-node-observations/v1",
          observation_source: "satori_on_node_detected",
          nodes: observations
        },
        null,
        2
      ) + "\n"
    );
  }
}
main();
