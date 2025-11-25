import { useEffect, useState } from 'react'

interface Stats {
  total_servers: number
  active_provisions: number
  logs_today: number
  denied_today: number
}

function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    // In a real app, fetch from API
    setStats({
      total_servers: 1247,
      active_provisions: 89,
      logs_today: 45892,
      denied_today: 127,
    })
  }, [])

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm mb-2">Active Servers</div>
          <div className="text-3xl font-bold text-green-400">{stats?.total_servers || 0}</div>
          <div className="text-xs text-gray-500 mt-2">↑ +12 this week</div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm mb-2">Active Provisions</div>
          <div className="text-3xl font-bold text-cyan-400">{stats?.active_provisions || 0}</div>
          <div className="text-xs text-gray-500 mt-2">↑ +3 today</div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm mb-2">Logs Today</div>
          <div className="text-3xl font-bold text-blue-400">{stats?.logs_today || 0}</div>
          <div className="text-xs text-gray-500 mt-2">↑ +5% vs yesterday</div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <div className="text-gray-400 text-sm mb-2">Denied Today</div>
          <div className="text-3xl font-bold text-red-400">{stats?.denied_today || 0}</div>
          <div className="text-xs text-gray-500 mt-2">↓ -8% vs yesterday</div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-green-400 mb-4">Recent Sudo Activity</h3>
          <div className="space-y-3">
            {[
              { user: 'jsmith', server: 'webserver01', command: 'systemctl restart nginx', result: 'ACCEPT' },
              { user: 'dbadmin', server: 'dbserver01', command: 'psql -U postgres', result: 'ACCEPT' },
              { user: 'unknown', server: 'webserver02', command: 'rm -rf /var/log/*', result: 'DENY' },
            ].map((log, idx) => (
              <div key={idx} className="bg-black border border-gray-800 rounded p-3 font-mono text-xs">
                <div className="flex justify-between mb-1">
                  <span className="text-cyan-400">{log.user}@{log.server}</span>
                  <span className={log.result === 'ACCEPT' ? 'text-green-400' : 'text-red-400'}>
                    {log.result}
                  </span>
                </div>
                <div className="text-gray-400 truncate">{log.command}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-yellow-400 mb-4">Expiring Soon</h3>
          <div className="space-y-3">
            {[
              { principal: 'DOMAIN\\ops-team', servers: '12 hosts', expires: '2h 34m' },
              { principal: 'jsmith', servers: 'webserver01', expires: '5h 12m' },
              { principal: 'DOMAIN\\contractors', servers: '5 hosts', expires: '23h 45m' },
            ].map((prov, idx) => (
              <div key={idx} className="bg-black border border-gray-800 rounded p-3">
                <div className="flex justify-between mb-1">
                  <span className="text-green-400 font-semibold">{prov.principal}</span>
                  <span className="text-yellow-400 text-sm">{prov.expires}</span>
                </div>
                <div className="text-gray-500 text-sm">{prov.servers}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Activity Chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-green-400 mb-4">Sudo Activity (7 Days)</h3>
        <div className="h-48 flex items-end justify-between gap-2">
          {[1200, 1450, 1850, 2100, 2300, 1900, 2400].map((value, idx) => (
            <div key={idx} className="flex-1 flex flex-col items-center">
              <div
                className="w-full bg-green-900 border border-green-700 rounded-t"
                style={{ height: `${(value / 2500) * 100}%` }}
              />
              <div className="text-xs text-gray-500 mt-2">
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][idx]}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
