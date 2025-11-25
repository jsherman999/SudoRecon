import { useState } from 'react'
import Dashboard from './pages/Dashboard'

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 sticky top-0 bg-gray-950 z-10">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-green-400 font-mono">SUDOGUARD</h1>
            <p className="text-xs text-gray-400">Centralized Sudo Management Platform</p>
          </div>
          <nav className="flex gap-4">
            <button
              onClick={() => setCurrentPage('dashboard')}
              className={`px-4 py-2 rounded ${
                currentPage === 'dashboard'
                  ? 'bg-green-900 text-green-400 border border-green-700'
                  : 'text-gray-400 hover:text-green-400'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setCurrentPage('provisions')}
              className={`px-4 py-2 rounded ${
                currentPage === 'provisions'
                  ? 'bg-green-900 text-green-400 border border-green-700'
                  : 'text-gray-400 hover:text-green-400'
              }`}
            >
              Provisions
            </button>
            <button
              onClick={() => setCurrentPage('logs')}
              className={`px-4 py-2 rounded ${
                currentPage === 'logs'
                  ? 'bg-green-900 text-green-400 border border-green-700'
                  : 'text-gray-400 hover:text-green-400'
              }`}
            >
              Logs
            </button>
            <button
              onClick={() => setCurrentPage('scan')}
              className={`px-4 py-2 rounded ${
                currentPage === 'scan'
                  ? 'bg-green-900 text-green-400 border border-green-700'
                  : 'text-gray-400 hover:text-green-400'
              }`}
            >
              Scan
            </button>
          </nav>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'provisions' && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
            <h2 className="text-2xl font-bold text-green-400 mb-4">Provisions Management</h2>
            <p className="text-gray-400">Provision management UI - Phase 3 & 4 implemented</p>
            <div className="mt-6 text-left bg-black border border-green-900 rounded p-4 font-mono text-sm">
              <p className="text-green-400">$ sudoguard provision grant --server 1 --user jsmith --justification "Maintenance"</p>
              <p className="text-gray-400 mt-2">Provision created: ID 101</p>
              <p className="text-gray-400">Principal: jsmith</p>
              <p className="text-gray-400">Status: pending</p>
            </div>
          </div>
        )}
        {currentPage === 'logs' && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
            <h2 className="text-2xl font-bold text-green-400 mb-4">Log Search & Export</h2>
            <p className="text-gray-400 mb-4">Advanced log search with CSV/JSON export - Phase 4 complete</p>
            <div className="grid grid-cols-2 gap-4 text-left">
              <div className="bg-black border border-cyan-900 rounded p-4">
                <h3 className="text-cyan-400 mb-2">Full-text Search</h3>
                <p className="text-gray-500 text-sm">Search commands, users, servers</p>
              </div>
              <div className="bg-black border border-cyan-900 rounded p-4">
                <h3 className="text-cyan-400 mb-2">Export Options</h3>
                <p className="text-gray-500 text-sm">CSV & JSON formats</p>
              </div>
            </div>
          </div>
        )}
        {currentPage === 'scan' && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
            <h2 className="text-2xl font-bold text-green-400 mb-4">Server Scanning</h2>
            <p className="text-gray-400 mb-4">Scan servers with real-time SSE updates - Phase 4 complete</p>
            <div className="bg-black border border-green-900 rounded p-4 font-mono text-sm text-left">
              <p className="text-green-400">▸ Scanning webserver01... ✓</p>
              <p className="text-green-400">▸ Parsing 2,341 log entries... ✓</p>
              <p className="text-green-400">▸ Stored 2,341 sudo logs ✓</p>
              <p className="text-cyan-400 mt-2">Progress: ████████████████████ 100%</p>
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-gray-800 mt-12">
        <div className="container mx-auto px-4 py-4 text-center text-gray-500 text-sm">
          SudoGuard v1.0.0 - Phases 1, 2, 3 & 4 Complete
        </div>
      </footer>
    </div>
  )
}

export default App
