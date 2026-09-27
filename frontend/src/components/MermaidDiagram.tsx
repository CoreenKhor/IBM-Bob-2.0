import { useEffect, useRef } from 'react'
import mermaid from 'mermaid'

interface Props {
  diagram: string
}

let idCounter = 0

mermaid.initialize({ startOnLoad: false, theme: 'neutral' })

export default function MermaidDiagram({ diagram }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const idRef = useRef(`mermaid-${++idCounter}`)

  useEffect(() => {
    if (!ref.current) return
    const id = idRef.current
    mermaid.render(id, diagram).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg
    })
  }, [diagram])

  return <div ref={ref} className="overflow-x-auto" />
}
