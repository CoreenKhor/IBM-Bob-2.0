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
  const [collapsedSidebar, setCollapsedSidebar] = useState(false)

  const codeFiles = files.filter(
    (f) =>
      f.type === 'file' &&
      !f.path.endsWith('__init__.py') &&
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

  if (collapsedSidebar) {
    return (
      <aside className="w-12 shrink-0 border-r border-gray-200 bg-white flex flex-col items-center py-3 select-none h-full">
        <button
          onClick={() => setCollapsedSidebar(false)}
          title="Expand File Tree"
          className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-800 transition-colors"
        >
          <span className="text-lg">📁</span>
        </button>
        <span className="text-[10px] text-gray-400 font-mono rotate-90 mt-6 tracking-wider whitespace-nowrap">
          FILES
        </span>
      </aside>
    )
  }

  return (
    <aside className="w-56 shrink-0 border-r border-gray-200 bg-white flex flex-col h-full select-none">
      {/* Sidebar Header with Collapse Button */}
      <div className="px-3 py-2.5 border-b border-gray-200 bg-gray-50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-xs font-semibold text-gray-600 uppercase tracking-wider truncate">
            demo / ecommerce
          </span>
        </div>
        <button
          onClick={() => setCollapsedSidebar(true)}
          title="Collapse Sidebar"
          className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-700 transition-colors text-xs"
        >
          ◀
        </button>
      </div>

      {/* Internal Independent Scroll Area */}
      <div className="py-1 flex-1 overflow-y-auto overscroll-contain">
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
                  <span className="text-[10px] text-gray-400">{isOpen ? '▾' : '▸'}</span>
                  <span>{icon}</span>
                  <span>{dir}</span>
                  <span className="ml-auto text-gray-400 font-mono text-[10px] font-normal normal-case">
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
                            className={`w-full text-left pl-8 pr-3 py-1.5 text-xs truncate transition-colors font-mono ${
                              isSelected
                                ? 'bg-blue-100 text-blue-700 font-semibold border-r-2 border-blue-600'
                                : 'text-gray-600 hover:bg-blue-50/70 hover:text-gray-900'
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

