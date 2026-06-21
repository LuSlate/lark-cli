export function node(type, style, children) {
  return { type, props: { style, children } }
}

export function box(style, children = []) {
  return node('div', { display: 'flex', boxSizing: 'border-box', ...style }, children)
}

export function TextBlock(value, style = {}) {
  return node(
    'div',
    {
      display: 'flex',
      boxSizing: 'border-box',
      whiteSpace: 'normal',
      ...style
    },
    value
  )
}

export function Title(value, style = {}) {
  return TextBlock(value, {
    fontSize: 58,
    fontWeight: 800,
    lineHeight: 1.05,
    ...style
  })
}

export function Subtitle(value, style = {}) {
  return TextBlock(value, {
    fontSize: 24,
    fontWeight: 500,
    lineHeight: 1.25,
    ...style
  })
}

export function Badge(value, style = {}) {
  return TextBlock(value, {
    fontSize: 18,
    fontWeight: 700,
    ...style
  })
}

export function Chip(value, style = {}) {
  return TextBlock(value, {
    minWidth: 92,
    height: 40,
    padding: '8px 15px',
    fontSize: 17,
    fontWeight: 600,
    ...style
  })
}

export function StatCard({ index, label, color, textColor, panelColor, style = {} }) {
  return box(
    {
      width: 250,
      minHeight: 126,
      flexDirection: 'column',
      backgroundColor: panelColor,
      padding: 22,
      ...style
    },
    [
      TextBlock(String(index).padStart(2, '0'), {
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
  )
}

export function ImageFrame({ children = [], style = {} }) {
  return box(
    {
      position: 'relative',
      overflow: 'hidden',
      backgroundColor: 'rgba(255,255,255,0.08)',
      ...style
    },
    children
  )
}
