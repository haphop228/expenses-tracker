import { useState, useCallback } from 'react'
import { AxiosError } from 'axios'
import toast from 'react-hot-toast'

interface UseApiState<T> {
  data: T | null
  isLoading: boolean
  error: string | null
}

interface UseApiReturn<T> extends UseApiState<T> {
  execute: (...args: unknown[]) => Promise<T | null>
  reset: () => void
}

export function useApi<T>(
  apiFunc: (...args: unknown[]) => Promise<T>,
  options: {
    onSuccess?: (data: T) => void
    onError?: (error: string) => void
    showErrorToast?: boolean
    showSuccessToast?: string
  } = {}
): UseApiReturn<T> {
  const { onSuccess, onError, showErrorToast = true, showSuccessToast } = options

  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    isLoading: false,
    error: null,
  })

  const execute = useCallback(
    async (...args: unknown[]): Promise<T | null> => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }))
      try {
        const result = await apiFunc(...args)
        setState({ data: result, isLoading: false, error: null })
        if (showSuccessToast) {
          toast.success(showSuccessToast)
        }
        onSuccess?.(result)
        return result
      } catch (err) {
        const axiosError = err as AxiosError<{ detail: string }>
        const message =
          axiosError.response?.data?.detail ||
          axiosError.message ||
          'Произошла ошибка'
        setState((prev) => ({ ...prev, isLoading: false, error: message }))
        if (showErrorToast) {
          toast.error(message)
        }
        onError?.(message)
        return null
      }
    },
    [apiFunc, onSuccess, onError, showErrorToast, showSuccessToast]
  )

  const reset = useCallback(() => {
    setState({ data: null, isLoading: false, error: null })
  }, [])

  return { ...state, execute, reset }
}
