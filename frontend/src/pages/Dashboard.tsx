import React, { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  TrendingDown,
  TrendingUp,
  Wallet,
  Receipt,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react'
import { format, startOfMonth, endOfMonth } from 'date-fns'
import { ru } from 'date-fns/locale'
import { expensesApi } from '../api/expenses'
import { budgetApi } from '../api/budget'
import { statisticsApi } from '../api/statistics'
import { useAuth } from '../contexts/AuthContext'
import type { Expense, BudgetResponse, StatsSummaryResponse } from '../types'

const formatAmount = (amount: number): string => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)
}

const Dashboard: React.FC = () => {
  const { user } = useAuth()
  const [recentExpenses, setRecentExpenses] = useState<Expense[]>([])
  const [budget, setBudget] = useState<BudgetResponse | null>(null)
  const [stats, setStats] = useState<StatsSummaryResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const currentMonth = format(new Date(), 'yyyy-MM')
  const monthStart = format(startOfMonth(new Date()), 'yyyy-MM-dd')
  const monthEnd = format(endOfMonth(new Date()), 'yyyy-MM-dd')

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [expensesData, budgetData, statsData] = await Promise.allSettled([
        expensesApi.getAll({ per_page: 5 }),
        budgetApi.get(currentMonth),
        statisticsApi.getSummary(monthStart, monthEnd),
      ])

      if (expensesData.status === 'fulfilled') {
        setRecentExpenses(expensesData.value.items)
      }
      if (budgetData.status === 'fulfilled') {
        setBudget(budgetData.value)
      }
      if (statsData.status === 'fulfilled') {
        setStats(statsData.value)
      }
    } finally {
      setIsLoading(false)
    }
  }, [currentMonth, monthStart, monthEnd])

  useEffect(() => {
    loadData()
  }, [loadData])

  const monthName = format(new Date(), 'LLLL yyyy', { locale: ru })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const budgetPercentage = budget?.percentage ?? null
  const budgetWarning = budgetPercentage !== null && budgetPercentage >= 80

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Привет, {user?.display_name || user?.username}! 👋
        </h1>
        <p className="text-gray-500 mt-1 capitalize">{monthName}</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Total spent */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500">Потрачено за месяц</span>
            <div className="w-9 h-9 bg-red-100 rounded-lg flex items-center justify-center">
              <TrendingDown size={18} className="text-red-600" />
            </div>
          </div>
          <p className="text-2xl font-bold text-gray-900">
            {formatAmount(stats?.total ?? 0)}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {stats?.by_category.length ?? 0} категорий
          </p>
        </div>

        {/* Budget */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500">Бюджет</span>
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${budgetWarning ? 'bg-yellow-100' : 'bg-green-100'}`}>
              {budgetWarning
                ? <AlertTriangle size={18} className="text-yellow-600" />
                : <Wallet size={18} className="text-green-600" />
              }
            </div>
          </div>
          {budget?.budget_limit ? (
            <>
              <p className="text-2xl font-bold text-gray-900">
                {formatAmount(budget.remaining ?? 0)}
              </p>
              <div className="mt-2">
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Использовано {budgetPercentage?.toFixed(0)}%</span>
                  <span>{formatAmount(budget.budget_limit)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all ${
                      budgetPercentage! >= 100
                        ? 'bg-red-500'
                        : budgetPercentage! >= 80
                        ? 'bg-yellow-500'
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.min(budgetPercentage!, 100)}%` }}
                  />
                </div>
              </div>
            </>
          ) : (
            <>
              <p className="text-2xl font-bold text-gray-400">—</p>
              <Link to="/budget" className="text-xs text-primary-600 hover:underline mt-1 block">
                Установить бюджет →
              </Link>
            </>
          )}
        </div>

        {/* Top category */}
        <div className="card sm:col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-gray-500">Топ категория</span>
            <div className="w-9 h-9 bg-purple-100 rounded-lg flex items-center justify-center">
              <TrendingUp size={18} className="text-purple-600" />
            </div>
          </div>
          {stats?.by_category[0] ? (
            <>
              <p className="text-2xl font-bold text-gray-900">
                {stats.by_category[0].emoji} {stats.by_category[0].category_name}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {formatAmount(stats.by_category[0].total)} · {stats.by_category[0].percentage.toFixed(0)}% расходов
              </p>
            </>
          ) : (
            <p className="text-2xl font-bold text-gray-400">—</p>
          )}
        </div>
      </div>

      {/* Budget warning */}
      {budgetWarning && budget && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle size={20} className="text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-800">
              Бюджет использован на {budgetPercentage?.toFixed(0)}%
            </p>
            <p className="text-xs text-yellow-600 mt-0.5">
              Осталось {formatAmount(budget.remaining ?? 0)} из {formatAmount(budget.budget_limit!)}
            </p>
          </div>
        </div>
      )}

      {/* Recent expenses */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
            <Receipt size={18} className="text-gray-400" />
            Последние расходы
          </h2>
          <Link
            to="/expenses"
            className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            Все <ArrowRight size={14} />
          </Link>
        </div>

        {recentExpenses.length === 0 ? (
          <div className="text-center py-8">
            <Receipt size={40} className="text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 text-sm">Расходов пока нет</p>
            <Link to="/expenses" className="btn-primary btn-sm mt-3 inline-flex">
              Добавить расход
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {recentExpenses.map((expense) => (
              <div
                key={expense.id}
                className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center text-lg">
                    {expense.category.emoji || '💰'}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {expense.category.name}
                    </p>
                    <p className="text-xs text-gray-400">
                      {expense.comment || expense.user.display_name || expense.user.username}
                      {' · '}
                      {format(new Date(expense.created_at), 'd MMM', { locale: ru })}
                    </p>
                  </div>
                </div>
                <span className="text-sm font-semibold text-gray-900">
                  {formatAmount(expense.amount)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Category breakdown */}
      {stats && stats.by_category.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-gray-900">По категориям</h2>
            <Link
              to="/statistics"
              className="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
            >
              Подробнее <ArrowRight size={14} />
            </Link>
          </div>
          <div className="space-y-3">
            {stats.by_category.slice(0, 5).map((cat) => (
              <div key={cat.category_id}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700">
                    {cat.emoji} {cat.category_name}
                  </span>
                  <span className="font-medium text-gray-900">
                    {formatAmount(cat.total)}
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-1.5">
                  <div
                    className="bg-primary-500 h-1.5 rounded-full"
                    style={{ width: `${cat.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
