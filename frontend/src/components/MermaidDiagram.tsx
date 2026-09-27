import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

interface Props {
  diagram: string
}

let idCounter = 0

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'loose',
})

export default function MermaidDiagram({ diagram }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [renderError, setRenderError] = useState<string | null>(null)

  useEffect(() => {
    if (!ref.current || !diagram?.trim()) return

    const uniqueId = `mermaid-svg-${Date.now()}-${++idCounter}`
    setRenderError(null)

    mermaid
      .render(uniqueId, diagram)
      .then(({ svg }) => {
        if (ref.current) {
          ref.current.innerHTML = svg
        }
      })
      .catch((err) => {
        console.warn('Mermaid render error:', err)
        setRenderError(String(err))
      })
  }, [diagram])

  if (renderError) {
    return (
      <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
        <p className="font-semibold">Diagram preview fallback:</p>
        <pre className="mt-1 p-2 bg-white rounded font-mono text-[11px] overflow-x-auto border border-amber-100">
          {diagram}
        </pre>
      </div>
    )
  }

  return <div ref={ref} className="overflow-x-auto flex justify-center py-2" />
}

