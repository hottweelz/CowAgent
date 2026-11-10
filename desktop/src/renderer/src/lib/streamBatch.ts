export type StreamBatchItem =
  | { type: 'reasoning'; target: string; content: string }
  | { type: 'delta'; target: string; content: string }
  | { type: 'tool_progress'; toolCallId: string; content: string | undefined }

/** Coalesce high-rate stream updates into a bounded batch per animation frame. */
export class StreamBatch {
  private items: StreamBatchItem[] = []
  private frame: number | null = null

  constructor(
    private readonly apply: (items: StreamBatchItem[]) => void,
    private readonly requestFrame: (callback: FrameRequestCallback) => number = requestAnimationFrame,
    private readonly cancelFrame: (id: number) => void = cancelAnimationFrame,
  ) {}

  reasoning(target: string, content: string) {
    this.queueText('reasoning', target, content)
  }

  delta(target: string, content: string) {
    this.queueText('delta', target, content)
  }

  progress(toolCallId: string, content: string | undefined) {
    if (!toolCallId) return
    const at = this.items.findIndex((item) => item.type === 'tool_progress' && item.toolCallId === toolCallId)
    const update: StreamBatchItem = { type: 'tool_progress', toolCallId, content }
    if (at < 0) this.items.push(update)
    else this.items[at] = update
    this.schedule()
  }

  flush() {
    if (this.frame !== null) {
      this.cancelFrame(this.frame)
      this.frame = null
    }
    if (!this.items.length) return

    const items = this.items
    this.items = []
    this.apply(items)
  }

  private queueText(type: 'reasoning' | 'delta', target: string, content: string) {
    const last = this.items[this.items.length - 1]
    if (last?.type === type && last.target === target) last.content += content
    else this.items.push({ type, target, content })
    this.schedule()
  }

  private schedule() {
    if (this.frame !== null) return
    this.frame = this.requestFrame(() => {
      this.frame = null
      this.flush()
    })
  }
}
