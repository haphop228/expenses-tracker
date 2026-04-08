import React, { useEffect, useState, useCallback } from 'react'
import {
  Users,
  Settings as SettingsIcon,
  Link,
  Copy,
  Check,
  Trash2,
  Shield,
  ShieldOff,
  Plus,
} from 'lucide-react'
import { groupsApi } from '../api/groups'
import { authApi } from '../api/auth'
import { categoriesApi } from '../api/categories'
import { useAuth } from '../contexts/AuthContext'
import toast from 'react-hot-toast'
import type { Member, GroupSettings, Category } from '../types'

const Settings: React.FC = () => {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<'group' | 'members' | 'categories' | 'telegram'>('group')
  const [members, setMembers] = useState<Member[]>([])
  const [settings, setSettings] = useState<GroupSettings | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [inviteCode, setInviteCode] = useState<string | null>(null)
  const [inviteExpires, setInviteExpires] = useState<string | null>(null)
  const [linkCode, setLinkCode] = useState<string | null>(null)
  const [linkCopied, setLinkCopied] = useState(false)
  const [inviteCopied, setInviteCopied] = useState(false)
  const [newCategoryName, setNewCategoryName] = useState('')
  const [newCategoryEmoji, setNewCategoryEmoji] = useState('')
  const [settingsForm, setSettingsForm] = useState<Partial<GroupSettings>>({})

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [membersData, settingsData, categoriesData] = await Promise.allSettled([
        groupsApi.getMembers(),
        groupsApi.getSettings(),
        categoriesApi.getAll(),
      ])
      if (membersData.status === 'fulfilled') setMembers(membersData.value)
      if (settingsData.status === 'fulfilled') {
        setSettings(settingsData.value)
        setSettingsForm(settingsData.value)
      }
      if (categoriesData.status === 'fulfilled') setCategories(categoriesData.value)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleGenerateInvite = async () => {
    try {
      const data = await groupsApi.generateInvite()
      setInviteCode(data.code)
      setInviteExpires(data.expires_at)
      toast.success('Инвайт-код создан')
    } catch {
      toast.error('Ошибка при создании инвайт-кода')
    }
  }

  const handleGenerateLinkCode = async () => {
    try {
      const data = await authApi.generateLinkCode()
      setLinkCode(data.link_code)
      toast.success('Код привязки создан')
    } catch {
      toast.error('Ошибка при создании кода привязки')
    }
  }

  const copyToClipboard = async (text: string, type: 'link' | 'invite') => {
    try {
      await navigator.clipboard.writeText(text)
      if (type === 'link') {
        setLinkCopied(true)
        setTimeout(() => setLinkCopied(false), 2000)
      } else {
        setInviteCopied(true)
        setTimeout(() => setInviteCopied(false), 2000)
      }
      toast.success('Скопировано!')
    } catch {
      toast.error('Не удалось скопировать')
    }
  }

  const handleRemoveMember = async (userId: number) => {
    if (!confirm('Удалить участника из группы?')) return
    try {
      await groupsApi.removeMember(userId)
      toast.success('Участник удалён')
      loadData()
    } catch {
      toast.error('Ошибка при удалении участника')
    }
  }

  const handleToggleAdmin = async (member: Member) => {
    try {
      await groupsApi.updateMemberRole(member.id, member.role !== 'admin')
      toast.success(member.role === 'admin' ? 'Права администратора сняты' : 'Права администратора выданы')
      loadData()
    } catch {
      toast.error('Ошибка при изменении прав')
    }
  }

  const handleSaveSettings = async () => {
    try {
      await groupsApi.updateSettings(settingsForm)
      toast.success('Настройки сохранены')
      loadData()
    } catch {
      toast.error('Ошибка при сохранении настроек')
    }
  }

  const handleAddCategory = async () => {
    if (!newCategoryName.trim()) {
      toast.error('Введите название категории')
      return
    }
    try {
      await categoriesApi.create(newCategoryName.trim(), newCategoryEmoji.trim() || undefined)
      toast.success('Категория добавлена')
      setNewCategoryName('')
      setNewCategoryEmoji('')
      loadData()
    } catch {
      toast.error('Ошибка при добавлении категории')
    }
  }

  const handleDeleteCategory = async (id: number) => {
    if (!confirm('Удалить категорию?')) return
    try {
      await categoriesApi.delete(id)
      toast.success('Категория удалена')
      loadData()
    } catch {
      toast.error('Ошибка при удалении категории')
    }
  }

  const tabs = [
    { id: 'group', label: 'Группа', icon: <SettingsIcon size={16} /> },
    { id: 'members', label: 'Участники', icon: <Users size={16} /> },
    { id: 'categories', label: 'Категории', icon: <SettingsIcon size={16} /> },
    { id: 'telegram', label: 'Telegram', icon: <Link size={16} /> },
  ] as const

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Настройки</h1>
        <p className="text-gray-500 text-sm mt-1">Управление группой и аккаунтом</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit flex-wrap">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {/* Group settings tab */}
          {activeTab === 'group' && (
            <div className="card space-y-4">
              <h2 className="text-base font-semibold text-gray-900">Настройки группы</h2>
              <div>
                <label className="label">Часовой пояс</label>
                <select
                  value={settingsForm.timezone ?? 'Europe/Moscow'}
                  onChange={(e) => setSettingsForm((f) => ({ ...f, timezone: e.target.value }))}
                  className="input"
                >
                  <option value="Europe/Moscow">Москва (UTC+3)</option>
                  <option value="Europe/Kaliningrad">Калининград (UTC+2)</option>
                  <option value="Europe/Samara">Самара (UTC+4)</option>
                  <option value="Asia/Yekaterinburg">Екатеринбург (UTC+5)</option>
                  <option value="Asia/Omsk">Омск (UTC+6)</option>
                  <option value="Asia/Krasnoyarsk">Красноярск (UTC+7)</option>
                  <option value="Asia/Irkutsk">Иркутск (UTC+8)</option>
                  <option value="Asia/Yakutsk">Якутск (UTC+9)</option>
                  <option value="Asia/Vladivostok">Владивосток (UTC+10)</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>
              <div>
                <label className="label">Валюта</label>
                <select
                  value={settingsForm.currency ?? 'RUB'}
                  onChange={(e) => setSettingsForm((f) => ({ ...f, currency: e.target.value }))}
                  className="input"
                >
                  <option value="RUB">₽ Рубль</option>
                  <option value="USD">$ Доллар</option>
                  <option value="EUR">€ Евро</option>
                  <option value="KZT">₸ Тенге</option>
                </select>
              </div>
              <div>
                <label className="label">Время напоминания</label>
                <input
                  type="time"
                  value={settingsForm.reminder_time ?? '20:00'}
                  onChange={(e) => setSettingsForm((f) => ({ ...f, reminder_time: e.target.value }))}
                  className="input w-40"
                />
              </div>
              <button onClick={handleSaveSettings} className="btn-primary">
                Сохранить настройки
              </button>
            </div>
          )}

          {/* Members tab */}
          {activeTab === 'members' && (
            <div className="space-y-4">
              {user?.role === 'admin' && (
                <div className="card">
                  <h2 className="text-base font-semibold text-gray-900 mb-3">Пригласить участника</h2>
                  <p className="text-sm text-gray-500 mb-3">
                    Создайте инвайт-код и передайте его новому участнику. Код действует 48 часов.
                  </p>
                  <button onClick={handleGenerateInvite} className="btn-primary btn-sm">
                    <Plus size={16} className="mr-1.5" />
                    Создать инвайт-код
                  </button>
                  {inviteCode && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2">
                        <code className="flex-1 text-sm font-mono text-gray-800 bg-white px-3 py-2 rounded border border-gray-200">
                          {inviteCode}
                        </code>
                        <button
                          onClick={() => copyToClipboard(inviteCode, 'invite')}
                          className="btn-secondary btn-sm"
                        >
                          {inviteCopied ? <Check size={16} className="text-green-600" /> : <Copy size={16} />}
                        </button>
                      </div>
                      {inviteExpires && (
                        <p className="text-xs text-gray-400 mt-1.5">
                          Действует до: {new Date(inviteExpires).toLocaleString('ru-RU')}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="card">
                <h2 className="text-base font-semibold text-gray-900 mb-4">
                  Участники ({members.length})
                </h2>
                <div className="space-y-3">
                  {members.map((member) => (
                    <div
                      key={member.id}
                      className="flex items-center gap-3 py-2 border-b border-gray-100 last:border-0"
                    >
                      <div className="w-9 h-9 bg-primary-100 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-primary-700 font-semibold text-sm">
                          {(member.name || member.web_login || '?')[0].toUpperCase()}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-900">
                            {member.name || member.web_login}
                          </span>
                          {member.role === 'admin' && (
                            <span className="badge-blue text-xs">Админ</span>
                          )}
                          {member.telegram_id && (
                            <span className="badge-green text-xs">TG</span>
                          )}
                        </div>
                        <p className="text-xs text-gray-400">@{member.web_login}</p>
                      </div>
                      {user?.role === 'admin' && member.id !== user.id && (
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleToggleAdmin(member)}
                            className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                            title={member.role === 'admin' ? 'Снять права' : 'Сделать админом'}
                          >
                            {member.role === 'admin' ? <ShieldOff size={15} /> : <Shield size={15} />}
                          </button>
                          <button
                            onClick={() => handleRemoveMember(member.id)}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Удалить участника"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Categories tab */}
          {activeTab === 'categories' && (
            <div className="space-y-4">
              {user?.role === 'admin' && (
                <div className="card">
                  <h2 className="text-base font-semibold text-gray-900 mb-3">Добавить категорию</h2>
                  <div className="flex gap-2 flex-wrap">
                    <input
                      type="text"
                      value={newCategoryEmoji}
                      onChange={(e) => setNewCategoryEmoji(e.target.value)}
                      className="input w-20 text-center text-xl"
                      placeholder="😀"
                      maxLength={2}
                    />
                    <input
                      type="text"
                      value={newCategoryName}
                      onChange={(e) => setNewCategoryName(e.target.value)}
                      className="input flex-1 min-w-40"
                      placeholder="Название категории"
                      onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()}
                    />
                    <button onClick={handleAddCategory} className="btn-primary btn-sm">
                      <Plus size={16} className="mr-1" />
                      Добавить
                    </button>
                  </div>
                </div>
              )}

              <div className="card">
                <h2 className="text-base font-semibold text-gray-900 mb-4">
                  Категории ({categories.length})
                </h2>
                <div className="space-y-2">
                  {categories.map((cat) => (
                    <div
                      key={cat.id}
                      className="flex items-center gap-3 py-2 border-b border-gray-100 last:border-0"
                    >
                      <span className="text-xl w-8 text-center">{cat.emoji || '💰'}</span>
                      <span className="flex-1 text-sm font-medium text-gray-900">{cat.name}</span>
                      {cat.exclude_from_budget && (
                        <span className="badge-gray text-xs">исключена из бюджета</span>
                      )}
                      {user?.role === 'admin' && (
                        <button
                          onClick={() => handleDeleteCategory(cat.id)}
                          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Telegram tab */}
          {activeTab === 'telegram' && (
            <div className="card">
              <h2 className="text-base font-semibold text-gray-900 mb-2">Привязка Telegram</h2>
              <p className="text-sm text-gray-500 mb-4">
                Привяжите ваш Telegram-аккаунт, чтобы использовать бота для добавления расходов.
              </p>

              {user?.telegram_id ? (
                <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200">
                  <Check size={20} className="text-green-600" />
                  <div>
                    <p className="text-sm font-medium text-green-800">Telegram привязан</p>
                    <p className="text-xs text-green-600">ID: {user.telegram_id}</p>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200 mb-4">
                    <p className="text-sm text-yellow-800">Telegram не привязан</p>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Для привязки:
                  </p>
                  <ol className="text-sm text-gray-600 space-y-2 mb-4 list-decimal list-inside">
                    <li>Нажмите кнопку ниже для получения кода</li>
                    <li>Откройте бота в Telegram</li>
                    <li>Отправьте команду <code className="bg-gray-100 px-1 rounded">/link КОД</code></li>
                  </ol>
                  <button onClick={handleGenerateLinkCode} className="btn-primary btn-sm mb-3">
                    Получить код привязки
                  </button>
                  {linkCode && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500 mb-2">Ваш код (действует 15 минут):</p>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 text-lg font-mono font-bold text-gray-900 bg-white px-3 py-2 rounded border border-gray-200 text-center tracking-widest">
                          {linkCode}
                        </code>
                        <button
                          onClick={() => copyToClipboard(linkCode, 'link')}
                          className="btn-secondary btn-sm"
                        >
                          {linkCopied ? <Check size={16} className="text-green-600" /> : <Copy size={16} />}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default Settings
