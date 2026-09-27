import { useState } from 'react'
import type { FileEntry } from '../types'

interface Props {
  files: FileEntry[]
  selectedFile: string
  onSelect: (path: string) => void
}

const DIR_ICONS: Record<string, string> = {
  services: '⚙',
  models: '📦',
  routes: '🛣',
  controllers: '🎛',
  tests: '🧪',
  schema: '🗄',
  frontend: '🖼',
}

export default function FileTree({ files, selectedFile, onSelect }: Props) {
  const codeFiles = files.filter(
    (f) =>
      f.type === 'file' &&
      (f.path.endsWith('.py') ||
        f.path.endsWith('.tsx') ||
        f.path.endsWith('.ts') ||
        f.path.endsWith('.jsx') ||
        f.path.endsWith('.js') ||
        f.path.endsWith('.sql'))
  )

  // Group by top-level directory
  const groups: Record<string, string[]> = {}
  for (const f of codeFiles) {

    const parts = f.path.split('/')
    const dir = parts.length > 1 ? parts[0] : '.'
    if (!groups[dir]) groups[dir] = []
    groups[dir].push(f.path)
  }

  // Track which groups are collapsed
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})
  const toggle = (dir: string) =>
    setCollapsed((prev) => ({ ...prev, [dir]: !prev[dir] }))

  return (
    <aside className="w-52 shrink-0 border-r border-gray-200 bg-white overflow-y-auto flex flex-col">
      <div className="px-3 py-2.5 border-b border-gray-200 bg-gray-50 shrink-0">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          demo / ecommerce
        </p>
      </div>

      <div className="py-1 flex-1 overflow-y-auto">
        {Object.entries(groups)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([dir, paths]) => {
            const isOpen = !collapsed[dir]
            const icon = DIR_ICONS[dir] ?? '📁'
            return (
              <div key={dir}>
                {/* Group header */}
                <button
                  onClick={() => toggle(dir)}
                  className="w-full flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-gray-500 hover:bg-gray-50 uppercase tracking-wider"
                >
                  <span>{isOpen ? '▾' : '▸'}</span>
                  <span>{icon}</span>
                  <span>{dir}</span>
                  <span className="ml-auto text-gray-300 font-normal normal-case">
                    {paths.length}
                  </span>
                </button>

                {/* File list */}
                {isOpen && (
                  <ul>
                    {paths.map((path) => {
                      const name = path.split('/').pop() ?? path
                      const isSelected = selectedFile === path
                      return (
                        <li key={path}>
                          <button
                            onClick={() => onSelect(path)}
                            title={path}
                            className={`w-full text-left pl-8 pr-3 py-1.5 text-xs truncate transition-colors ${
                              isSelected
                                ? 'bg-blue-100 text-blue-700 font-medium'
                                : 'text-gray-600 hover:bg-blue-50'
                            }`}
                          >
                            {name}
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            )
          })}
      </div>
    </aside>
  )
}
