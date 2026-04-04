import React, { useEffect, useState, useCallback } from 'react'
import { format, subMonths, addMonths } from 'date-fns'
import { ru } from 'date-fns/locale'
import { ChevronLeft, ChevronRight, Edit2, AlertTriangle, CheckCircle } from 'lucide-react'
import { budgetApi } from '../api/budget'
import toast from 'react-hot-toast'
import type { BudgetResponse } from '../types'

const formatAmount = (amount: number): string =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)

const Budget: React.FC = () => {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [budget, setBudget] = useState<BudgetResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [editingTotal, setEditingTotal] = useState(false)
  const [totalInput, setTotalInput] = useState('')
  const [editingCategory, setEditingCategory] = useState<number | null>(null)
  const [categoryInput, setCategoryInput] = useState('')

  const month = format(currentDate, 'yyyy-MM')
  const monthLabel = format(currentDate, 'LLLL yyyy', { locale: ru })

  const loadBudget = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await budgetApi.get(month)
      setBudget(data)
    } catch {
      toast.error('Ошибка загрузки бюджета')
    } finally {
      setIsLoading(false)
    }
  }, [month])

  useEffect(() => {
    loadBudget()
  }, [loadBudget])

  const handleSetTotal = async () => {
    const amount = parseFloat(totalInput.replace(',', '.'))
    if (isNaN(amount) || amount <= 0) {
      toast.error('Введите корректную сумму')
      return
    }
    try {
      await budgetApi.set(month, amount)
      toast.success('Бюджет установлен')
      setEditingTotal(false)
      loadBudget()
    } catch {
      toast.error('Ошибка при установке бюджета')
    }
  }

  const handleSetCategoryLimit = async (categoryId: number) => {
    const amount = parseFloat(categoryInput.replace(',', '.'))
    if (isNaN(amount) || amount <= 0) {
      toast.error('Введите корректную сумму')
      return
    }
    try {
      await budgetApi.setCategoryLimit(month, categoryId, amount)
      toast.success('Лимит установлен')
      setEditingCategory(null)
      loadBudget()
    } catch {
      toast.error('Ошибка при установке лимита')
    }
  }

  const getProgressColor = (percentage: number | null) => {
    if (percentage === null) return 'bg-gray-300'
    if (percentage >= 100) return 'bg-red-500'
    if (percentage >= 80) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <div className="space-y-6">
      {/* Header with month navigation */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Бюджет</h1>
          <p className="text-gray-500 text-sm mt-1 capitalize">{monthLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentDate((d) => subMonths(d, 1))}
            className="btn-secondary btn-sm"
          >
            <ChevronLeft size={16} />
          </button>
          <button
            onClick={() => setCurrentDate(new Date())}
            className="btn-secondary btn-sm text-xs"
          >
            Сейчас
          </button>
          <button
            onClick={() => setCurrentDate((d) => addMonths(d, 1))}
            className="btn-secondary btn-sm"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Total budget card */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-gray-900">Общий бюджет</h2>
              <button
                onClick={() => {
                  setTotalInput(budget?.budget_limit ? String(budget.budget_limit) : '')
                  setEditingTotal(true)
                }}
                className="btn-secondary btn-sm"
              >
                <Edit2 size={14} className="mr-1" />
                {budget?.budget_limit ? 'Изменить' : 'Установить'}
              </button>
            </div>

            {editingTotal ? (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={totalInput}
                  onChange={(e) => setTotalInput(e.target.value)}
                  className="input flex-1"
                  placeholder="Сумма бюджета"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleSetTotal()}
                />
                <button onClick={handleSetTotal} className="btn-primary btn-sm">
                  Сохранить
                </button>
                <button onClick={() => setEditingTotal(false)} className="btn-secondary btn-sm">
                  Отмена
                </button>
              </div>
            ) : budget?.budget_limit ? (
              <div>
                <div className="flex justify-between items-end mb-2">
                  <div>
                    <p className="text-3xl font-bold text-gray-900">
                      {formatAmount(budget.remaining ?? 0)}
                    </p>
                    <p className="text-sm text-gray-500 mt-0.5">
                      осталось из {formatAmount(budget.budget_limit)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-gray-700">
                      {formatAmount(budget.total_spent)}
                    </p>
                    <p className="text-xs text-gray-400">потрачено</p>
                  </div>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${getProgressColor(budget.percentage)}`}
                    style={{ width: `${Math.min(budget.percentage ?? 0, 100)}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-xs text-gray-400">
                    {budget.percentage?.toFixed(0) ?? 0}% использовано
                  </span>
                  {(budget.percentage ?? 0) >= 100 && (
                    <span className="text-xs text-red-600 flex items-center gap-1">
                      <AlertTriangle size={12} />
                      Превышен!
                    </span>
                  )}
                  {(budget.percentage ?? 0) < 80 && (
                    <span className="text-xs text-green-600 flex items-center gap-1">
                      <CheckCircle size={12} />
                      В норме
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-gray-400 text-sm">Бюджет не установлен</p>
                <p className="text-gray-400 text-xs mt-1">
                  Потрачено: {formatAmount(budget?.total_spent ?? 0)}
                </p>
              </div>
            )}
          </div>

          {/* By category */}
          {budget && budget.by_category.length > 0 && (
            <div className="card">
              <h2 className="text-base font-semibold text-gray-900 mb-4">По категориям</h2>
              <div className="space-y-4">
                {budget.by_category.map((cat) => (
                  <div key={cat.category_id} className={cat.exclude_from_budget ? 'opacity-50' : ''}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{cat.emoji || '💰'}</span>
                        <span className="text-sm font-medium text-gray-800">
                          {cat.category_name}
                        </span>
                        {cat.exclude_from_budget && (
                          <span className="badge-gray text-xs">исключена</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-gray-900">
                          {formatAmount(cat.spent)}
                        </span>
                        {cat.budget_limit && (
                          <span className="text-xs text-gray-400">
                            / {formatAmount(cat.budget_limit)}
                          </span>
                        )}
                        <button
                          onClick={() => {
                            setEditingCategory(cat.category_id)
                            setCategoryInput(cat.budget_limit ? String(cat.budget_limit) : '')
                          }}
                          className="p-1 text-gray-400 hover:text-primary-600 rounded"
                        >
                          <Edit2 size={13} />
                        </button>
                      </div>
                    </div>

                    {editingCategory === cat.category_id ? (
                      <div className="flex gap-2 mt-2">
                        <input
                          type="text"
                          value={categoryInput}
                          onChange={(e) => setCategoryInput(e.target.value)}
                          className="input flex-1 text-sm py-1.5"
                          placeholder="Лимит для категории"
                          autoFocus
                          onKeyDown={(e) =>
                            e.key === 'Enter' && handleSetCategoryLimit(cat.category_id)
                          }
                        />
                        <button
                          onClick={() => handleSetCategoryLimit(cat.category_id)}
                          className="btn-primary btn-sm"
                        >
                          ОК
                        </button>
                        <button
                          onClick={() => setEditingCategory(null)}
                          className="btn-secondary btn-sm"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${getProgressColor(cat.percentage)}`}
                          style={{ width: `${Math.min(cat.percentage ?? 0, 100)}%` }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default Budget
