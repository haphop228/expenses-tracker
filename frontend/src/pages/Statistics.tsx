import React, { useEffect, useState, useCallback } from 'react'
import { format, startOfMonth, endOfMonth, subMonths } from 'date-fns'
import { ru } from 'date-fns/locale'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { statisticsApi } from '../api/statistics'
import type { StatsSummaryResponse } from '../types'

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#6366f1',
]

const formatAmount = (amount: number): string =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)

const PERIOD_OPTIONS = [
  { label: 'Этот месяц', value: 'current' },
  { label: 'Прошлый месяц', value: 'prev' },
  { label: 'Последние 3 месяца', value: '3months' },
  { label: 'Произвольный', value: 'custom' },
]

const Statistics: React.FC = () => {
  const [stats, setStats] = useState<StatsSummaryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [period, setPeriod] = useState('current')
  const [dateFrom, setDateFrom] = useState(format(startOfMonth(new Date()), 'yyyy-MM-dd'))
  const [dateTo, setDateTo] = useState(format(endOfMonth(new Date()), 'yyyy-MM-dd'))
  const [activeTab, setActiveTab] = useState<'category' | 'user'>('category')

  const applyPeriod = useCallback((p: string) => {
    const now = new Date()
    if (p === 'current') {
      setDateFrom(format(startOfMonth(now), 'yyyy-MM-dd'))
      setDateTo(format(endOfMonth(now), 'yyyy-MM-dd'))
    } else if (p === 'prev') {
      const prev = subMonths(now, 1)
      setDateFrom(format(startOfMonth(prev), 'yyyy-MM-dd'))
      setDateTo(format(endOfMonth(prev), 'yyyy-MM-dd'))
    } else if (p === '3months') {
      setDateFrom(format(startOfMonth(subMonths(now, 2)), 'yyyy-MM-dd'))
      setDateTo(format(endOfMonth(now), 'yyyy-MM-dd'))
    }
  }, [])

  useEffect(() => {
    applyPeriod(period)
  }, [period, applyPeriod])

  const loadStats = useCallback(async () => {
    if (!dateFrom || !dateTo) return
    setIsLoading(true)
    try {
      const data = await statisticsApi.getSummary(dateFrom, dateTo)
      setStats(data)
    } catch {
      // ignore
    } finally {
      setIsLoading(false)
    }
  }, [dateFrom, dateTo])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  const categoryData = stats?.by_category.map((c) => ({
    name: `${c.emoji || ''} ${c.category_name}`,
    value: c.total,
    percentage: c.percentage,
  })) ?? []

  const userData = stats?.by_user.map((u) => ({
    name: u.display_name || u.username,
    value: u.total,
    percentage: u.percentage,
  })) ?? []

  const periodLabel = (() => {
    if (!dateFrom || !dateTo) return ''
    const from = format(new Date(dateFrom), 'd MMM', { locale: ru })
    const to = format(new Date(dateTo), 'd MMM yyyy', { locale: ru })
    return `${from} — ${to}`
  })()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Статистика</h1>
        <p className="text-gray-500 text-sm mt-1">{periodLabel}</p>
      </div>

      {/* Period selector */}
      <div className="card">
        <div className="flex flex-wrap gap-2 mb-4">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              className={`btn btn-sm ${period === opt.value ? 'btn-primary' : 'btn-secondary'}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        {period === 'custom' && (
          <div className="flex gap-3 flex-wrap">
            <div>
              <label className="label">С даты</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="input"
              />
            </div>
            <div>
              <label className="label">По дату</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="input"
              />
            </div>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : !stats || stats.total === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-400">Нет данных за выбранный период</p>
        </div>
      ) : (
        <>
          {/* Total */}
          <div className="card">
            <p className="text-sm text-gray-500 mb-1">Итого за период</p>
            <p className="text-3xl font-bold text-gray-900">{formatAmount(stats.total)}</p>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
            <button
              onClick={() => setActiveTab('category')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'category'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              По категориям
            </button>
            <button
              onClick={() => setActiveTab('user')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'user'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              По участникам
            </button>
          </div>

          {activeTab === 'category' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Pie chart */}
              <div className="card">
                <h3 className="text-base font-semibold text-gray-900 mb-4">Распределение</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={categoryData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={110}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {categoryData.map((_, index) => (
                        <Cell key={index} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value: number) => formatAmount(value)}
                    />
                    <Legend
                      formatter={(value) => (
                        <span className="text-xs text-gray-600">{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Category list */}
              <div className="card">
                <h3 className="text-base font-semibold text-gray-900 mb-4">Детализация</h3>
                <div className="space-y-3">
                  {stats.by_category.map((cat, index) => (
                    <div key={cat.category_id}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-700 flex items-center gap-1.5">
                          <span
                            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          {cat.emoji} {cat.category_name}
                        </span>
                        <span className="font-medium text-gray-900">
                          {formatAmount(cat.total)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full"
                            style={{
                              width: `${cat.percentage}%`,
                              backgroundColor: COLORS[index % COLORS.length],
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-400 w-10 text-right">
                          {cat.percentage.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'user' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Bar chart */}
              <div className="card">
                <h3 className="text-base font-semibold text-gray-900 mb-4">По участникам</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={userData} layout="vertical">
                    <XAxis type="number" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                    <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(value: number) => formatAmount(value)} />
                    <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* User list */}
              <div className="card">
                <h3 className="text-base font-semibold text-gray-900 mb-4">Детализация</h3>
                <div className="space-y-3">
                  {stats.by_user.map((user, index) => (
                    <div key={user.user_id}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-700 flex items-center gap-1.5">
                          <span
                            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                            style={{ backgroundColor: COLORS[index % COLORS.length] }}
                          />
                          {user.display_name || user.username}
                        </span>
                        <span className="font-medium text-gray-900">
                          {formatAmount(user.total)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full"
                            style={{
                              width: `${user.percentage}%`,
                              backgroundColor: COLORS[index % COLORS.length],
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-400 w-10 text-right">
                          {user.percentage.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default Statistics
