import { useState } from 'react'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-green-400">SUDOGUARD</h1>
          <p className="text-sm text-gray-400">Centralized Sudo Management Platform</p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          <h2 className="text-xl font-semibold mb-4 text-green-400">
            Welcome to SudoGuard
          </h2>
          <p className="text-gray-300 mb-6">
            Phase 1 and 2 implementation complete.
          </p>
          <div className="space-y-4">
            <div className="text-left bg-black border border-green-900 rounded p-4 font-mono text-sm">
              <p className="text-green-400">$ sudoguard --help</p>
              <p className="text-gray-400 mt-2">Usage: sudoguard [OPTIONS] COMMAND [ARGS]...</p>
              <p className="text-gray-400">Commands:</p>
              <p className="text-gray-400 ml-4">scan      Scan servers for sudo logs</p>
              <p className="text-gray-400 ml-4">servers   Manage server inventory</p>
              <p className="text-gray-400 ml-4">logs      Search and export sudo logs</p>
            </div>

            <div className="grid grid-cols-3 gap-4 mt-6">
              <div className="bg-black border border-gray-800 rounded p-4">
                <h3 className="text-green-400 font-semibold mb-2">API</h3>
                <p className="text-gray-400 text-sm">FastAPI + PostgreSQL</p>
              </div>
              <div className="bg-black border border-gray-800 rounded p-4">
                <h3 className="text-green-400 font-semibold mb-2">CLI</h3>
                <p className="text-gray-400 text-sm">Click + Rich output</p>
              </div>
              <div className="bg-black border border-gray-800 rounded p-4">
                <h3 className="text-green-400 font-semibold mb-2">Web UI</h3>
                <p className="text-gray-400 text-sm">React + TypeScript</p>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-gray-800 mt-12">
        <div className="container mx-auto px-4 py-4 text-center text-gray-500 text-sm">
          SudoGuard v1.0.0 - Phases 1 & 2 Complete
        </div>
      </footer>
    </div>
  )
}

export default App
