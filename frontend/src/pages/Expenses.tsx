import React, { useEffect, useState, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import { Plus, Search, Filter, Trash2, Edit2, ChevronLeft, ChevronRight, X } from 'lucide-react'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { expensesApi } from '../api/expenses'
import { categoriesApi } from '../api/categories'
import toast from 'react-hot-toast'
import type { Expense, Category, ExpenseCreate, ExpenseFilters } from '../types'

const formatAmount = (amount: number): string =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)

const SELECT_STYLE = {
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
  backgroundRepeat: 'no-repeat' as const,
  backgroundPosition: 'right 8px center',
}

const MONTHS = [
  'Январь','Февраль','Март','Апрель','Май','Июнь',
  'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь',
]

interface DateSelectPickerProps {
  value: string // yyyy-MM-dd
  onChange: (value: string) => void
  disabled?: boolean
}

const DateSelectPicker: React.FC<DateSelectPickerProps> = ({ value, onChange, disabled }) => {
  const [year, month, day] = value.split('-').map(Number)

  const daysInMonth = new Date(year, month, 0).getDate()
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1)
  const months = MONTHS.map((name, i) => ({ value: i + 1, name }))
  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i)

  const update = (d: number, m: number, y: number) => {
    const maxDay = new Date(y, m, 0).getDate()
    const safeDay = Math.min(d, maxDay)
    onChange(`${y}-${String(m).padStart(2, '0')}-${String(safeDay).padStart(2, '0')}`)
  }

  const selectClass = 'px-2 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 appearance-none cursor-pointer pr-6'

  return (
    <div className="flex gap-2">
      <select
        value={day}
        onChange={(e) => update(Number(e.target.value), month, year)}
        className={`${selectClass} w-20`}
        style={SELECT_STYLE}
        disabled={disabled}
      >
        {days.map((d) => (
          <option key={d} value={d}>{String(d).padStart(2, '0')}</option>
        ))}
      </select>
      <select
        value={month}
        onChange={(e) => update(day, Number(e.target.value), year)}
        className={`${selectClass} flex-1`}
        style={SELECT_STYLE}
        disabled={disabled}
      >
        {months.map((m) => (
          <option key={m.value} value={m.value}>{m.name}</option>
        ))}
      </select>
      <select
        value={year}
        onChange={(e) => update(day, month, Number(e.target.value))}
        className={`${selectClass} w-24`}
        style={SELECT_STYLE}
        disabled={disabled}
      >
        {years.map((y) => (
          <option key={y} value={y}>{y}</option>
        ))}
      </select>
    </div>
  )
}

interface ExpenseModalProps {
  expense?: Expense | null
  categories: Category[]
  onClose: () => void
  onSave: () => void
}

const ExpenseModal: React.FC<ExpenseModalProps> = ({ expense, categories, onClose, onSave }) => {
  const [categoryId, setCategoryId] = useState<number>(expense?.category_id ?? (categories[0]?.id ?? 0))
  const [amount, setAmount] = useState(expense ? String(expense.amount) : '')
  const [comment, setComment] = useState(expense?.comment ?? '')
  const [date, setDate] = useState(
    expense ? format(new Date(expense.created_at), 'yyyy-MM-dd') : format(new Date(), 'yyyy-MM-dd')
  )
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    // Строгая валидация: допускаем только цифры с опциональной точкой/запятой
    const trimmed = amount.trim().replace(',', '.')
    if (!/^\d+(\.\d+)?$/.test(trimmed)) {
      toast.error('Введите корректную сумму (только цифры)')
      return
    }
    const amountNum = parseFloat(trimmed)
    if (isNaN(amountNum) || amountNum <= 0) {
      toast.error('Сумма должна быть больше нуля')
      return
    }
    if (!categoryId) {
      toast.error('Выберите категорию')
      return
    }
    setIsLoading(true)
    try {
      if (expense) {
        await expensesApi.update(expense.id, {
          amount: amountNum,
          comment: comment || undefined,
          category_id: categoryId,
        })
        toast.success('Расход обновлён')
      } else {
        const data: ExpenseCreate = {
          category_id: categoryId,
          amount: amountNum,
          comment: comment || undefined,
          created_at: date,
        }
        await expensesApi.create(data)
        toast.success('Расход добавлен')
      }
      onSave()
      onClose()
    } catch {
      toast.error('Ошибка при сохранении')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            {expense ? 'Редактировать расход' : 'Добавить расход'}
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="label">Категория</label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(Number(e.target.value))}
              className="block w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 appearance-none cursor-pointer"
              style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 12px center' }}
              disabled={isLoading}
            >
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.emoji} {cat.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Сумма (₽)</label>
            <input
              type="text"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="input text-lg font-semibold"
              placeholder="Например: 350"
              disabled={isLoading}
              autoFocus
            />
          </div>
          <div>
            <label className="label">Комментарий</label>
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="input"
              placeholder="Необязательно"
              disabled={isLoading}
            />
          </div>
          <div>
            <label className="label">Дата</label>
            <DateSelectPicker value={date} onChange={setDate} disabled={isLoading} />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
              disabled={isLoading}
            >
              Отмена
            </button>
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={isLoading}
            >
              {isLoading ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

const Expenses: React.FC = () => {
  const location = useLocation()
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editExpense, setEditExpense] = useState<Expense | null>(null)
  const [filters, setFilters] = useState<ExpenseFilters>(() => {
    const state = location.state as { filters?: ExpenseFilters; user_name?: string; excludeBudgetExcluded?: boolean } | null
    return state?.filters ? { per_page: 20, ...state.filters } : { per_page: 20 }
  })
  const [filterUserName, setFilterUserName] = useState<string | undefined>(() => {
    const state = location.state as { filters?: ExpenseFilters; user_name?: string } | null
    return state?.user_name
  })
  // Задача 3: флаг "только бюджетные категории" из Statistics
  const [filterExcludeBudget, setFilterExcludeBudget] = useState<boolean>(() => {
    const state = location.state as { excludeBudgetExcluded?: boolean } | null
    return state?.excludeBudgetExcluded ?? false
  })
  const [showFilters, setShowFilters] = useState(() => {
    const state = location.state as { filters?: ExpenseFilters } | null
    return !!(state?.filters)
  })
  const [searchComment, setSearchComment] = useState('')

  const loadExpenses = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await expensesApi.getAll({ ...filters, page })
      setExpenses(data.items)
      setTotal(data.total)
      setPages(data.pages)
    } catch {
      toast.error('Ошибка загрузки расходов')
    } finally {
      setIsLoading(false)
    }
  }, [filters, page])

  useEffect(() => {
    loadExpenses()
  }, [loadExpenses])

  useEffect(() => {
    categoriesApi.getAll().then(setCategories).catch(() => {})
  }, [])

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить этот расход?')) return
    try {
      await expensesApi.delete(id)
      toast.success('Расход удалён')
      loadExpenses()
    } catch {
      toast.error('Ошибка при удалении')
    }
  }

  const handleEdit = (expense: Expense) => {
    setEditExpense(expense)
    setShowModal(true)
  }

  const handleModalClose = () => {
    setShowModal(false)
    setEditExpense(null)
  }

  const filteredExpenses = searchComment
    ? expenses.filter((e) =>
        e.comment?.toLowerCase().includes(searchComment.toLowerCase()) ||
        (e.category_name ?? '').toLowerCase().includes(searchComment.toLowerCase())
      )
    : expenses

  // Активные фильтры (кроме per_page) для отображения бейджей
  const activeFilterCount = [
    filters.category_id,
    filters.user_id,
    filters.date_from,
    filters.date_to,
    filterExcludeBudget || undefined,
  ].filter(Boolean).length

  const activeCategoryName = filters.category_id
    ? categories.find((c) => c.id === filters.category_id)
    : null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Расходы</h1>
          <p className="text-gray-500 text-sm mt-1">Всего: {total}</p>
        </div>
        <button
          onClick={() => { setEditExpense(null); setShowModal(true) }}
          className="btn-primary"
        >
          <Plus size={18} className="mr-1.5" />
          Добавить
        </button>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex gap-3 flex-wrap">
          <div className="flex-1 min-w-48 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchComment}
              onChange={(e) => setSearchComment(e.target.value)}
              className="input pl-9"
              placeholder="Поиск по комментарию..."
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary relative ${showFilters ? 'bg-primary-50 border-primary-300 text-primary-700' : ''}`}
          >
            <Filter size={16} className="mr-1.5" />
            Фильтры
            {activeFilterCount > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-primary-600 text-white text-xs rounded-full flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Активные фильтры — бейджи */}
        {activeFilterCount > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {activeCategoryName && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary-50 text-primary-700 text-xs rounded-full border border-primary-200">
                {activeCategoryName.emoji} {activeCategoryName.name}
                <button onClick={() => { setFilters((f) => ({ ...f, category_id: undefined })); setPage(1) }}>
                  <X size={12} />
                </button>
              </span>
            )}
            {filters.user_id && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary-50 text-primary-700 text-xs rounded-full border border-primary-200">
                👤 {filterUserName ?? `Участник #${filters.user_id}`}
                <button onClick={() => { setFilters((f) => ({ ...f, user_id: undefined })); setFilterUserName(undefined); setPage(1) }}>
                  <X size={12} />
                </button>
              </span>
            )}
            {filters.date_from && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary-50 text-primary-700 text-xs rounded-full border border-primary-200">
                С {filters.date_from}
                <button onClick={() => { setFilters((f) => ({ ...f, date_from: undefined })); setPage(1) }}>
                  <X size={12} />
                </button>
              </span>
            )}
            {filters.date_to && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-primary-50 text-primary-700 text-xs rounded-full border border-primary-200">
                По {filters.date_to}
                <button onClick={() => { setFilters((f) => ({ ...f, date_to: undefined })); setPage(1) }}>
                  <X size={12} />
                </button>
              </span>
            )}
            {filterExcludeBudget && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-orange-50 text-orange-700 text-xs rounded-full border border-orange-200">
                Только бюджетные
                <button onClick={() => setFilterExcludeBudget(false)}>
                  <X size={12} />
                </button>
              </span>
            )}
            <button
              onClick={() => { setFilters({ per_page: 20 }); setFilterUserName(undefined); setFilterExcludeBudget(false); setPage(1) }}
              className="inline-flex items-center gap-1 px-2 py-1 text-gray-500 text-xs hover:text-red-600 transition-colors"
            >
              <X size={12} /> Сбросить все
            </button>
          </div>
        )}

        {showFilters && (
          <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="label">Категория</label>
              <select
                value={filters.category_id ?? ''}
                onChange={(e) => setFilters((f) => ({ ...f, category_id: e.target.value ? Number(e.target.value) : undefined }))}
                className="block w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 appearance-none cursor-pointer"
                style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 12px center' }}
              >
                <option value="">Все категории</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.emoji} {cat.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">С даты</label>
              <DateSelectPicker
                value={filters.date_from ?? format(new Date(), 'yyyy-MM-dd')}
                onChange={(v) => setFilters((f) => ({ ...f, date_from: v }))}
              />
            </div>
            <div>
              <label className="label">По дату</label>
              <DateSelectPicker
                value={filters.date_to ?? format(new Date(), 'yyyy-MM-dd')}
                onChange={(v) => setFilters((f) => ({ ...f, date_to: v }))}
              />
            </div>
            <div className="sm:col-span-3 flex gap-2">
              <button
                onClick={() => { setFilters({ per_page: 20 }); setFilterUserName(undefined); setFilterExcludeBudget(false); setPage(1) }}
                className="btn-secondary btn-sm"
              >
                Сбросить
              </button>
              <button
                onClick={() => { setPage(1); loadExpenses() }}
                className="btn-primary btn-sm"
              >
                Применить
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Expenses list */}
      <div className="card p-0 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-40">
            <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filteredExpenses.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-400 text-sm">Расходов не найдено</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredExpenses.map((expense) => (
              <div
                key={expense.id}
                className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center text-xl flex-shrink-0">
                  {expense.category_emoji || '💰'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">
                      {expense.category_name || '—'}
                    </span>
                    {expense.user_name && (
                      <span className="badge-gray text-xs">
                        {expense.user_name}
                      </span>
                    )}
                  </div>
                  {expense.comment && (
                    <p className="text-xs text-gray-500 truncate mt-0.5">{expense.comment}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-0.5">
                    {format(new Date(expense.created_at), 'd MMMM yyyy', { locale: ru })}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-base font-semibold text-gray-900 whitespace-nowrap">
                    {formatAmount(expense.amount)}
                  </span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleEdit(expense)}
                      className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                      title="Редактировать"
                    >
                      <Edit2 size={15} />
                    </button>
                    <button
                      onClick={() => handleDelete(expense.id)}
                      className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Удалить"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200">
            <p className="text-sm text-gray-500">
              Страница {page} из {pages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary btn-sm"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page === pages}
                className="btn-secondary btn-sm"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <ExpenseModal
          expense={editExpense}
          categories={categories}
          onClose={handleModalClose}
          onSave={loadExpenses}
        />
      )}
    </div>
  )
}

export default Expenses
