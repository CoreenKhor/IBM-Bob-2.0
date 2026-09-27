import { useState, useEffect } from 'react'
import type { FileEntry, BlastRadiusReport } from './types'
import { fetchTree, fetchAnalysis } from './api'
import FileTree from './components/FileTree'
import AnalyzeForm from './components/AnalyzeForm'
import ImpactReport from './components/ImpactReport'

export default function App() {
  const [files, setFiles] = useState<FileEntry[]>([])
  const [selectedFile, setSelectedFile] = useState('')
  const [report, setReport] = useState<BlastRadiusReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [treeError, setTreeError] = useState<string | null>(null)

  useEffect(() => {
    fetchTree()
      .then((data) => setFiles(data.files))
      .catch((e) => setTreeError(String(e)))
  }, [])

  const handleAnalyze = async (symbol: string, description: string, changeType: string) => {
    setLoading(true)
    setError(null)
    setReport(null)
    try {
      const result = await fetchAnalysis({
        target_file: selectedFile,
        target_symbol: symbol,
        change_description: description,
        change_type: changeType,
      })
      setReport(result)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-50 overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3.5 flex items-center gap-3 shrink-0 z-10">
        <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center text-base shrink-0">💥</div>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-bold text-gray-900 leading-tight">
            Change Blast Radius Analyzer
          </h1>
          <p className="text-xs text-gray-400">IBM Bob 2.0 Hackathon · Developer Workflow Accelerator</p>
        </div>
        <div className="hidden sm:flex items-center gap-2 text-xs text-gray-400">
          <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
          demo/ecommerce
        </div>
      </header>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Sidebar — file tree with independent scroll & collapse */}
        {treeError ? (
          <div className="w-56 border-r border-gray-200 p-4 text-xs text-red-600 bg-white shrink-0">
            ⚠ {treeError}
          </div>
        ) : (
          <FileTree files={files} selectedFile={selectedFile} onSelect={setSelectedFile} />
        )}

        {/* Main layout container */}
        <div className="flex-1 flex overflow-hidden min-w-0">
          {/* Left panel — sticky form & demo scenarios with dedicated scroll */}
          <div className="w-80 shrink-0 h-full overflow-y-auto border-r border-gray-200 bg-white p-5">
            <AnalyzeForm
              targetFile={selectedFile}
              onFileSelect={setSelectedFile}
              onSubmit={handleAnalyze}
              loading={loading}
            />
            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 leading-relaxed">
                <span className="font-semibold">Error: </span>{error}
              </div>
            )}
          </div>

          {/* Right panel — impact report with independent scroll */}
          <main className="flex-1 h-full overflow-y-auto p-6 min-w-0 bg-gray-50">
            {!report && !loading && (
              <div className="h-full min-h-[400px] flex items-center justify-center text-center text-gray-400 select-none">
                <div>
                  <div className="text-6xl mb-5 opacity-60">💥</div>
                  <p className="text-sm font-medium text-gray-500">Ready to analyze</p>
                  <p className="text-xs text-gray-400 mt-1 max-w-xs mx-auto">
                    Click a demo scenario on the left, or select a file and symbol to trace the blast radius.
                  </p>
                </div>
              </div>
            )}
            {loading && (
              <div className="h-full min-h-[400px] flex items-center justify-center text-center">
                <div>
                  <div className="text-5xl mb-5 animate-pulse">⚡</div>
                  <p className="text-sm font-medium text-gray-600">Tracing dependencies…</p>
                  <p className="text-xs text-gray-400 mt-1">Building the blast radius map</p>
                </div>
              </div>
            )}
            {report && <ImpactReport report={report} />}
          </main>
        </div>
      </div>
    </div>
  )
}
