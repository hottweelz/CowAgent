export interface Rect { x: number; y: number; width: number; height: number }
export interface DisplayArea { workArea: Rect }
export interface DisplayProvider {
  getAllDisplays(): DisplayArea[]
  getPrimaryDisplay(): DisplayArea
}

export type WindowBounds = { width: number; height: number; x?: number; y?: number }

const MIN_VISIBLE_PX = 100

export function isOnSomeDisplay(bounds: Rect, screen: DisplayProvider): boolean {
  return screen.getAllDisplays().some(({ workArea }) => {
    const width = Math.min(bounds.x + bounds.width, workArea.x + workArea.width) - Math.max(bounds.x, workArea.x)
    const height = Math.min(bounds.y + bounds.height, workArea.y + workArea.height) - Math.max(bounds.y, workArea.y)
    return width >= MIN_VISIBLE_PX && height >= MIN_VISIBLE_PX
  })
}

export function sanitizeWindowState(state: WindowBounds, screen: DisplayProvider): WindowBounds {
  if (typeof state.x === 'number' && typeof state.y === 'number' && isOnSomeDisplay({
    x: state.x,
    y: state.y,
    width: state.width,
    height: state.height,
  }, screen)) {
    // A valid secondary display may be larger than the primary display.
    return state
  }

  const workArea = screen.getPrimaryDisplay().workArea
  const width = Math.min(Math.max(state.width, 900), workArea.width)
  const height = Math.min(Math.max(state.height, 600), workArea.height)
  return { width, height }
}

export function centeredVisibleBounds(bounds: Rect, screen: DisplayProvider): Rect {
  const workArea = screen.getPrimaryDisplay().workArea
  const width = Math.min(bounds.width, workArea.width)
  const height = Math.min(bounds.height, workArea.height)
  return {
    x: Math.round(workArea.x + (workArea.width - width) / 2),
    y: Math.round(workArea.y + (workArea.height - height) / 2),
    width,
    height,
  }
}
