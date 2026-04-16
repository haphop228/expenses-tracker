import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Users,
  Building2,
  Plus,
  Trash2,
  LogOut,
  Shield,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  RefreshCw,
} from 'lucide-react'
import { adminApi } from '../../api/admin'
import toast from 'react-hot-toast'
import type { AdminGroupResponse, AdminGroupDetail } from '../../types/admin'

const AdminDashboard: React.FC = () => {
  const navigate = useNavigate()
  const [groups, setGroups] = useState<AdminGroupResponse[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newGroupName, setNewGroupName] = useState('')
  const [selectedGroup, setSelectedGroup] = useState<AdminGroupResponse | null>(null)
  const [inviteCode, setInviteCode] = useState<string | null>(null)
  const [inviteCopied, setInviteCopied] = useState(false)
  const [expandedGroupId, setExpandedGroupId] = useState<number | null>(null)
  const [groupDetail, setGroupDetail] = useState<AdminGroupDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [resetPasswordUserId, setResetPasswordUserId] = useState<number | null>(null)
  const [resetPasswordValue, setResetPasswordValue] = useState('')
  const [resetPasswordLoading, setResetPasswordLoading] = useState(false)

  const perPage = 20
  const pages = Math.ceil(total / perPage)

  const loadGroups = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await adminApi.getGroups(page, perPage)
      setGroups(data.items)
      setTotal(data.total)
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } }
      if (error?.response?.status === 401) {
        localStorage.removeItem('admin_token')
        navigate('/admin/login')
      } else {
        toast.error('Ошибка загрузки групп')
      }
    } finally {
      setIsLoading(false)
    }
  }, [page, navigate])

  useEffect(() => {
    const token = localStorage.getItem('admin_token')
    if (!token) {
      navigate('/admin/login')
      return
    }
    loadGroups()
  }, [loadGroups, navigate])

  const handleLogout = () => {
    localStorage.removeItem('admin_token')
    navigate('/admin/login')
    toast.success('Вы вышли из панели администратора')
  }

  const handleCreateGroup = async () => {
    if (!newGroupName.trim()) {
      toast.error('Введите название группы')
      return
    }
    try {
      await adminApi.createGroup(newGroupName.trim())
      toast.success('Группа создана')
      setShowCreateModal(false)
      setNewGroupName('')
      loadGroups()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      toast.error(error?.response?.data?.detail || 'Ошибка при создании группы')
    }
  }

  const handleDeleteGroup = async (group: AdminGroupResponse) => {
    if (!confirm(`Удалить группу "${group.name}"? Это действие необратимо!`)) return
    try {
      await adminApi.deleteGroup(group.id)
      toast.success('Группа удалена')
      if (expandedGroupId === group.id) setExpandedGroupId(null)
      loadGroups()
    } catch {
      toast.error('Ошибка при удалении группы')
    }
  }

  const handleGenerateInvite = async (group: AdminGroupResponse) => {
    try {
      const data = await adminApi.generateInvite(group.id)
      setInviteCode(data.code)
      setSelectedGroup(group)
      toast.success('Инвайт-код создан')
    } catch {
      toast.error('Ошибка при создании инвайт-кода')
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
      setInviteCopied(true)
      setTimeout(() => setInviteCopied(false), 2000)
      toast.success('Скопировано!')
    } catch {
      toast.error('Не удалось скопировать')
    }
  }

  const handleToggleExpand = async (group: AdminGroupResponse) => {
    if (expandedGroupId === group.id) {
      setExpandedGroupId(null)
      setGroupDetail(null)
      return
    }
    setExpandedGroupId(group.id)
    setDetailLoading(true)
    try {
      const detail = await adminApi.getGroup(group.id)
      setGroupDetail(detail)
    } catch {
      toast.error('Ошибка загрузки деталей группы')
    } finally {
      setDetailLoading(false)
    }
  }

  const handleResetPassword = async (userId: number, userName: string) => {
    const newPassword = prompt(`Новый пароль для ${userName} (мин. 8 символов):`)
    if (!newPassword || newPassword.length < 8) {
      if (newPassword !== null) toast.error('Пароль должен быть не менее 8 символов')
      return
    }
    setResetPasswordLoading(true)
    try {
      await adminApi.resetUserPassword(userId, newPassword)
      toast.success(`Пароль пользователя ${userName} сброшен`)
    } catch {
      toast.error('Ошибка при сбросе пароля')
    } finally {
      setResetPasswordLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center">
              <Shield size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Панель администратора</h1>
              <p className="text-xs text-gray-400">Управление группами и пользователями</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
          >
            <LogOut size={16} />
            Выйти
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 bg-blue-600/20 rounded-lg flex items-center justify-center">
                <Building2 size={18} className="text-blue-400" />
              </div>
              <span className="text-sm text-gray-400">Всего групп</span>
            </div>
            <p className="text-3xl font-bold text-white">{total}</p>
          </div>
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-9 h-9 bg-green-600/20 rounded-lg flex items-center justify-center">
                <Users size={18} className="text-green-400" />
              </div>
              <span className="text-sm text-gray-400">Всего участников</span>
            </div>
            <p className="text-3xl font-bold text-white">
              {groups.reduce((sum, g) => sum + g.members_count, 0)}
            </p>
          </div>
        </div>

        {/* Groups table */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
            <h2 className="text-base font-semibold text-white">Группы</h2>
            <div className="flex gap-2">
              <button
                onClick={loadGroups}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                title="Обновить"
              >
                <RefreshCw size={15} />
              </button>
              <button
                onClick={() => setShowCreateModal(true)}
                className="flex items-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                <Plus size={16} />
                Создать группу
              </button>
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center h-40">
              <div className="w-8 h-8 border-4 border-red-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : groups.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              Групп пока нет. Создайте первую группу.
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Группа
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Участники
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Расходы
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                        За месяц
                      </th>
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">
                        Создана
                      </th>
                      <th className="px-6 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700">
                    {groups.map((group) => (
                      <React.Fragment key={group.id}>
                        <tr
                          className="hover:bg-gray-750 transition-colors cursor-pointer"
                          onClick={() => handleToggleExpand(group)}
                        >
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              {expandedGroupId === group.id
                                ? <ChevronUp size={14} className="text-gray-400 flex-shrink-0" />
                                : <ChevronDown size={14} className="text-gray-400 flex-shrink-0" />
                              }
                              <p className="text-sm font-medium text-white">{group.name}</p>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-sm text-gray-300">{group.members_count}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-sm text-gray-300">{group.expenses_count}</span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-sm text-gray-300">
                              {Number(group.total_spent_month).toLocaleString('ru-RU')} ₽
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <span className="text-xs text-gray-400">
                              {new Date(group.created_at).toLocaleDateString('ru-RU')}
                            </span>
                          </td>
                          <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-1 justify-end">
                              <button
                                onClick={() => handleGenerateInvite(group)}
                                className="p-1.5 text-gray-400 hover:text-blue-400 hover:bg-blue-900/30 rounded-lg transition-colors"
                                title="Создать инвайт-код"
                              >
                                <Plus size={15} />
                              </button>
                              <button
                                onClick={() => handleDeleteGroup(group)}
                                className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-900/30 rounded-lg transition-colors"
                                title="Удалить"
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </td>
                        </tr>

                        {/* Expanded group detail */}
                        {expandedGroupId === group.id && (
                          <tr>
                            <td colSpan={6} className="px-6 py-0">
                              <div className="bg-gray-750 border border-gray-700 rounded-xl my-3 overflow-hidden">
                                {detailLoading ? (
                                  <div className="flex items-center justify-center py-8">
                                    <div className="w-6 h-6 border-3 border-red-600 border-t-transparent rounded-full animate-spin" />
                                  </div>
                                ) : groupDetail && groupDetail.id === group.id ? (
                                  <div className="p-4 space-y-4">
                                    {/* Group info */}
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                      <div className="bg-gray-800 rounded-lg p-3">
                                        <p className="text-xs text-gray-400 mb-1">Участников</p>
                                        <p className="text-lg font-bold text-white">{groupDetail.statistics.members_count}</p>
                                      </div>
                                      <div className="bg-gray-800 rounded-lg p-3">
                                        <p className="text-xs text-gray-400 mb-1">Расходов всего</p>
                                        <p className="text-lg font-bold text-white">{groupDetail.statistics.total_expenses}</p>
                                      </div>
                                      <div className="bg-gray-800 rounded-lg p-3">
                                        <p className="text-xs text-gray-400 mb-1">За месяц</p>
                                        <p className="text-lg font-bold text-white">
                                          {Number(groupDetail.statistics.month_spent).toLocaleString('ru-RU')} ₽
                                        </p>
                                      </div>
                                      <div className="bg-gray-800 rounded-lg p-3">
                                        <p className="text-xs text-gray-400 mb-1">Создана</p>
                                        <p className="text-sm font-medium text-white">
                                          {new Date(groupDetail.created_at).toLocaleDateString('ru-RU')}
                                        </p>
                                      </div>
                                    </div>

                                    {/* Members list */}
                                    {groupDetail.members && groupDetail.members.length > 0 && (
                                      <div>
                                        <h4 className="text-sm font-semibold text-gray-300 mb-2 flex items-center gap-2">
                                          <Users size={14} />
                                          Участники ({groupDetail.members.length})
                                        </h4>
                                        <div className="space-y-2">
                                          {groupDetail.members.map((member) => (
                                            <div
                                              key={member.id}
                                              className="flex items-center gap-3 bg-gray-800 rounded-lg px-3 py-2"
                                            >
                                              <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center flex-shrink-0">
                                                <span className="text-gray-300 font-semibold text-xs">
                                                  {(member.name || member.web_login || '?')[0].toUpperCase()}
                                                </span>
                                              </div>
                                              <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                  <span className="text-sm font-medium text-white">
                                                    {member.name || member.web_login}
                                                  </span>
                                                  {member.role === 'admin' && (
                                                    <span className="text-xs bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded">
                                                      Админ
                                                    </span>
                                                  )}
                                                  {member.telegram_id && (
                                                    <span className="text-xs bg-green-900/50 text-green-300 px-1.5 py-0.5 rounded">
                                                      TG
                                                    </span>
                                                  )}
                                                </div>
                                                <p className="text-xs text-gray-500">@{member.web_login}</p>
                                              </div>
                                              <div className="text-right flex items-center gap-2">
                                                <p className="text-xs text-gray-400">
                                                  {member.created_at
                                                    ? `с ${new Date(member.created_at).toLocaleDateString('ru-RU')}`
                                                    : ''}
                                                </p>
                                                <button
                                                  onClick={() => handleResetPassword(member.id, member.name || member.web_login || 'пользователя')}
                                                  disabled={resetPasswordLoading}
                                                  className="text-xs text-yellow-400 hover:text-yellow-300 px-2 py-1 rounded border border-yellow-700 hover:border-yellow-500 transition-colors disabled:opacity-50"
                                                  title="Сбросить пароль"
                                                >
                                                  🔑
                                                </button>
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                ) : null}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {pages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t border-gray-700">
                  <p className="text-sm text-gray-400">
                    Страница {page} из {pages}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <button
                      onClick={() => setPage((p) => Math.min(pages, p + 1))}
                      disabled={page === pages}
                      className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* Create group modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-xl shadow-xl w-full max-w-md border border-gray-700">
            <div className="px-6 py-4 border-b border-gray-700">
              <h2 className="text-lg font-semibold text-white">Создать группу</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Название группы
                </label>
                <input
                  type="text"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  className="block w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500 text-sm"
                  placeholder="Моя семья"
                  autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateGroup()}
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => { setShowCreateModal(false); setNewGroupName('') }}
                  className="flex-1 py-2 px-4 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Отмена
                </button>
                <button
                  onClick={handleCreateGroup}
                  className="flex-1 py-2 px-4 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  Создать
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Invite code modal */}
      {inviteCode && selectedGroup && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-xl shadow-xl w-full max-w-md border border-gray-700">
            <div className="px-6 py-4 border-b border-gray-700">
              <h2 className="text-lg font-semibold text-white">
                Инвайт-код для «{selectedGroup.name}»
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-gray-400">
                Передайте этот код новому участнику. Код действует 48 часов.
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-lg font-mono font-bold text-white bg-gray-700 px-4 py-3 rounded-lg text-center tracking-widest border border-gray-600">
                  {inviteCode}
                </code>
                <button
                  onClick={() => copyToClipboard(inviteCode)}
                  className="p-3 bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded-lg transition-colors"
                >
                  {inviteCopied ? <Check size={18} className="text-green-400" /> : <Copy size={18} />}
                </button>
              </div>
              <div className="bg-gray-700/50 rounded-lg p-3 border border-gray-600">
                <p className="text-xs text-gray-400 mb-1">Ссылка для регистрации:</p>
                <p className="text-xs font-mono text-blue-400 break-all">
                  {(import.meta.env.VITE_PUBLIC_URL || window.location.origin)}/register/{inviteCode}
                </p>
              </div>
              <p className="text-xs text-gray-500">
                💡 Пользователь должен перейти по ссылке выше и зарегистрироваться. После этого он сможет войти через <strong className="text-gray-400">/login</strong>.
              </p>
              <button
                onClick={() => { setInviteCode(null); setSelectedGroup(null) }}
                className="w-full py-2 px-4 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminDashboard
