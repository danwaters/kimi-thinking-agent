import { useState, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './index.css'

interface Turn {
  number: number
  status: 'processing' | 'completed'
  thinking?: string
  toolCalls: Array<{
    name: string
    args: Record<string, unknown>
    result: unknown
  }>
}

interface AnalysisState {
  status: 'idle' | 'loading' | 'done' | 'error'
  company: string
  turns: Turn[]
  analysis: string
  error?: string
}

function App() {
  const [company, setCompany] = useState('Tesla')
  const [state, setState] = useState<AnalysisState>({
    status: 'idle',
    company: '',
    turns: [],
    analysis: '',
  })
  const abortControllerRef = useRef<AbortController | null>(null)

  const analyzeCompany = async () => {
    // Abort any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    setState({
      status: 'loading',
      company,
      turns: [],
      analysis: '',
    })

    try {
      const response = await fetch('http://localhost:8000/analyze/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: company }),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''
      let currentTurn: Turn | null = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = JSON.parse(line.slice(6))

          switch (data.type) {
            case 'turn_start':
              currentTurn = { number: data.turn, status: 'processing', toolCalls: [] }
              setState(s => ({ ...s, turns: [...s.turns, currentTurn!] }))
              break

            case 'thinking':
              if (currentTurn) {
                currentTurn.thinking = data.content
                setState(s => ({
                  ...s,
                  turns: s.turns.map(t =>
                    t.number === currentTurn!.number ? { ...currentTurn! } : t
                  ),
                }))
              }
              break

            case 'tool_call':
              if (currentTurn) {
                currentTurn.toolCalls.push({
                  name: data.name,
                  args: data.args,
                  result: data.result,
                })
                setState(s => ({
                  ...s,
                  turns: s.turns.map(t =>
                    t.number === currentTurn!.number ? { ...currentTurn! } : t
                  ),
                }))
              }
              break

            case 'turn_end':
              if (currentTurn) {
                currentTurn.status = 'completed'
                setState(s => ({
                  ...s,
                  turns: s.turns.map(t =>
                    t.number === currentTurn!.number ? { ...currentTurn! } : t
                  ),
                }))
              }
              break

            case 'analysis':
              setState(s => ({ ...s, analysis: data.content }))
              break

            case 'done':
              setState(s => ({ ...s, status: 'done' }))
              break

            case 'error':
              setState(s => ({ ...s, status: 'error', error: data.message }))
              break
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setState(s => ({
          ...s,
          status: 'error',
          error: (err as Error).message,
        }))
      }
    }
  }

  return (
    <div className="min-h-screen p-8 text-slate-200">
      {/* Header */}
      <header className="max-w-4xl mx-auto mb-8">
        <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-[#00d4aa] to-[#00a8ff] mb-2">
          🔮 Together AI Deep Market Researcher
        </h1>
        <p className="text-slate-400">
          Powered by Kimi K2-Thinking on Together AI · Watch the AI reason through complex analysis
        </p>
      </header>

      {/* Input */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="flex gap-4">
          <input
            type="text"
            value={company}
            onChange={e => setCompany(e.target.value)}
            placeholder="Enter company name..."
            className="flex-1 px-4 py-3 bg-[#1a1a2e] border border-[#2d2d44] rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#00d4aa] transition-colors"
            onKeyDown={e => e.key === 'Enter' && analyzeCompany()}
          />
          <button
            onClick={analyzeCompany}
            disabled={state.status === 'loading'}
            className="px-6 py-3 bg-gradient-to-r from-[#00d4aa] to-[#00a8ff] text-[#0f0f1a] font-semibold rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {state.status === 'loading' ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Analyzing...
              </span>
            ) : (
              'Analyze'
            )}
          </button>
        </div>
      </div>

      {/* Results */}
      {(state.turns.length > 0 || state.analysis) && (
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Turns - show all turns that have content or are processing */}
          {state.turns.map(turn => (
            <TurnCard key={turn.number} turn={turn} />
          ))}

          {/* Final Analysis */}
          {state.analysis && (
            <div className="bg-[#1a1a2e] border border-[#00d4aa40] rounded-xl overflow-hidden">
              <div className="px-5 py-3 bg-gradient-to-r from-[#00d4aa20] to-transparent border-b border-[#00d4aa40]">
                <h3 className="text-lg font-semibold text-[#00d4aa] flex items-center gap-2">
                  📊 Final Analysis
                </h3>
              </div>
              <div className="p-5 markdown-content text-slate-300">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{state.analysis}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* Error */}
          {state.status === 'error' && (
            <div className="bg-red-900/30 border border-red-500/50 rounded-xl p-5">
              <p className="text-red-400">❌ Error: {state.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TurnCard({ turn }: { turn: Turn }) {
  const [thinkingExpanded, setThinkingExpanded] = useState(true) // Default expanded to show thinking
  const isEmpty = turn.toolCalls.length === 0 && !turn.thinking

  return (
    <div className="bg-[#1a1a2e] border border-[#2d2d44] rounded-xl overflow-hidden">
      {/* Turn Header */}
      <div className="px-5 py-3 bg-[#2d2d44]/50 border-b border-[#2d2d44] flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
          Turn {turn.number}
        </h3>
        {turn.status === 'completed' && (
          <span className="text-xs text-green-500">✓ Complete</span>
        )}
      </div>

      <div className="p-5 space-y-4">
        {/* Thinking Section */}
        {turn.thinking && (
          <div className="bg-gradient-to-r from-purple-900/20 to-indigo-900/20 border border-purple-500/30 rounded-lg overflow-hidden">
            <button
              onClick={() => setThinkingExpanded(!thinkingExpanded)}
              className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-purple-900/20 transition-colors"
            >
              <span className="text-sm font-medium text-purple-300 flex items-center gap-2">
                🧠 Reasoning
                <span className="text-xs text-purple-400/60 font-normal">
                  ({turn.thinking.length.toLocaleString()} chars)
                </span>
              </span>
              <svg
                className={`w-4 h-4 text-purple-400 transition-transform ${thinkingExpanded ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {thinkingExpanded && (
              <div className="px-4 py-3 border-t border-purple-500/20 font-mono text-xs text-purple-200/80 whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">
                {turn.thinking}
              </div>
            )}
          </div>
        )}

        {/* Tool Calls */}
        {turn.toolCalls.map((tc, i) => (
          <div key={i} className="bg-[#fbbf2410] border border-[#fbbf2430] rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className="text-lg">🔧</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono text-sm font-semibold text-[#fbbf24]">
                    {tc.name}
                  </span>
                  <span className="font-mono text-xs text-slate-500">
                    ({JSON.stringify(tc.args)})
                  </span>
                </div>
                <div className="font-mono text-xs text-slate-400 bg-[#0f0f1a] rounded p-2 overflow-x-auto">
                  → {JSON.stringify(tc.result, null, 2)}
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator for processing turn */}
        {isEmpty && turn.status === 'processing' && (
          <div className="flex items-center gap-2 text-slate-500">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-sm">Waiting for model response...</span>
          </div>
        )}

        {/* Message for empty completed turns */}
        {isEmpty && turn.status === 'completed' && (
          <div className="text-sm text-slate-500 italic">
            Internal processing (no visible output)
          </div>
        )}
      </div>
    </div>
  )
}

export default App
