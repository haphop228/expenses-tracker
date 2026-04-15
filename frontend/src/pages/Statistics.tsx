import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { format, startOfMonth, endOfMonth, subMonths, startOfWeek, endOfWeek } from 'date-fns'
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
import { COLORS, getColorById } from '../constants'

const formatAmount = (amount: number): string =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)

const PERIOD_OPTIONS = [
  { label: 'Сегодня', value: 'today' },
  { label: 'Неделя', value: 'week' },
  { label: 'Этот месяц', value: 'current' },
  { label: 'Прошлый месяц', value: 'prev' },
  { label: 'Последние 3 месяца', value: '3months' },
  { label: 'Произвольный', value: 'custom' },
]

const Statistics: React.FC = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState<StatsSummaryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [period, setPeriod] = useState('current')
  const [dateFrom, setDateFrom] = useState(format(startOfMonth(new Date()), 'yyyy-MM-dd'))
  const [dateTo, setDateTo] = useState(format(endOfMonth(new Date()), 'yyyy-MM-dd'))
  const [activeTab, setActiveTab] = useState<'category' | 'user'>('category')
  const [excludeBudgetExcluded, setExcludeBudgetExcluded] = useState(false)

  const goToExpenses = useCallback((filters: { category_id?: number; user_id?: number; user_name?: string; date_from?: string; date_to?: string }) => {
    const { user_name, ...filterFields } = filters
    navigate('/expenses', { state: { filters: { ...filterFields, date_from: dateFrom, date_to: dateTo }, user_name } })
  }, [navigate, dateFrom, dateTo])

  const applyPeriod = useCallback((p: string) => {
    const now = new Date()
    if (p === 'today') {
      const today = format(now, 'yyyy-MM-dd')
      setDateFrom(today)
      setDateTo(today)
    } else if (p === 'week') {
      setDateFrom(format(startOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'))
      setDateTo(format(endOfWeek(now, { weekStartsOn: 1 }), 'yyyy-MM-dd'))
    } else if (p === 'current') {
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
      const data = await statisticsApi.getSummary(dateFrom, dateTo, excludeBudgetExcluded)
      setStats(data)
    } catch {
      // ignore
    } finally {
      setIsLoading(false)
    }
  }, [dateFrom, dateTo, excludeBudgetExcluded])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  const categoryData = stats?.by_category.map((c) => ({
    name: `${c.category_emoji || ''} ${c.category_name || ''}`.trim(),
    value: Number(c.total),
    percentage: c.percentage,
    fill: getColorById(c.category_id ?? 0),
  })) ?? []

  const userData = stats?.by_user.map((u) => ({
    name: u.user_name,
    value: Number(u.total),
    percentage: u.percentage,
    fill: getColorById(u.user_id),
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
        {/* Фильтр исключённых категорий */}
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-2">Учёт категорий в статистике:</p>
          <div className="flex gap-2">
            <button
              onClick={() => setExcludeBudgetExcluded(false)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                !excludeBudgetExcluded
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-primary-400 hover:text-primary-600'
              }`}
            >
              Все категории
            </button>
            <button
              onClick={() => setExcludeBudgetExcluded(true)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors border ${
                excludeBudgetExcluded
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-primary-400 hover:text-primary-600'
              }`}
            >
              Только бюджетные
            </button>
          </div>
          {excludeBudgetExcluded && (
            <p className="text-xs text-orange-500 mt-1.5">
              Категории, исключённые из бюджета, не учитываются
            </p>
          )}
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
      ) : !stats || stats.total_amount === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-400">Нет данных за выбранный период</p>
        </div>
      ) : (
        <>
          {/* Total */}
          <div className="card">
            <p className="text-sm text-gray-500 mb-1">Итого за период</p>
            <p className="text-3xl font-bold text-gray-900">{formatAmount(Number(stats.total_amount))}</p>
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
                      onClick={(_, index) => {
                        const cat = stats?.by_category[index]
                        if (cat) goToExpenses({ category_id: cat.category_id ?? undefined })
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      {categoryData.map((entry, index) => (
                        <Cell key={index} fill={entry.fill} />
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
                  {stats.by_category.map((cat) => {
                    const color = getColorById(cat.category_id ?? 0)
                    return (
                      <div
                        key={cat.category_id}
                        className="cursor-pointer hover:bg-gray-50 rounded-lg px-2 py-1 -mx-2 transition-colors group"
                        onClick={() => goToExpenses({ category_id: cat.category_id ?? undefined })}
                        title="Перейти к расходам по этой категории"
                      >
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-700 flex items-center gap-1.5 group-hover:text-primary-600 transition-colors">
                            <span
                              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                              style={{ backgroundColor: color }}
                            />
                            {cat.category_emoji} {cat.category_name}
                          </span>
                          <span className="font-medium text-gray-900 group-hover:text-primary-600 transition-colors">
                            {formatAmount(Number(cat.total))}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                            <div
                              className="h-1.5 rounded-full"
                              style={{ width: `${cat.percentage}%`, backgroundColor: color }}
                            />
                          </div>
                          <span className="text-xs text-gray-400 w-10 text-right">
                            {cat.percentage.toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    )
                  })}
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
                    <Bar
                      dataKey="value"
                      radius={[0, 4, 4, 0]}
                      onClick={(_, index) => {
                        const user = stats?.by_user[index]
                        if (user) goToExpenses({ user_id: user.user_id, user_name: user.user_name })
                      }}
                      style={{ cursor: 'pointer' }}
                      isAnimationActive={false}
                    >
                      {userData.map((entry, index) => (
                        <Cell key={index} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* User list */}
              <div className="card">
                <h3 className="text-base font-semibold text-gray-900 mb-4">Детализация</h3>
                <div className="space-y-3">
                  {stats.by_user.map((user) => {
                    const color = getColorById(user.user_id)
                    return (
                      <div
                        key={user.user_id}
                        className="cursor-pointer hover:bg-gray-50 rounded-lg px-2 py-1 -mx-2 transition-colors group"
                        onClick={() => goToExpenses({ user_id: user.user_id, user_name: user.user_name })}
                        title="Перейти к расходам этого участника"
                      >
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-700 flex items-center gap-1.5 group-hover:text-primary-600 transition-colors">
                            <span
                              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                              style={{ backgroundColor: color }}
                            />
                            {user.user_name}
                          </span>
                          <span className="font-medium text-gray-900 group-hover:text-primary-600 transition-colors">
                            {formatAmount(Number(user.total))}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                            <div
                              className="h-1.5 rounded-full"
                              style={{ width: `${user.percentage}%`, backgroundColor: color }}
                            />
                          </div>
                          <span className="text-xs text-gray-400 w-10 text-right">
                            {user.percentage.toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    )
                  })}
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
