import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Logs } from './Logs'

vi.mock('@/lib/api', () => ({
    useLogs: vi.fn(),
    useSystemLogs: vi.fn(),
    useLogStats: vi.fn(),
    useProviders: vi.fn(),
}))

import * as api from '@/lib/api'

const AUTH_ERROR_TITLE = 'Authentication Error'
const AUTH_ERROR_MSG =
    'Unable to load data. Your Gateway Token may be missing or invalid. Please configure your token in the Settings.'

const defaultSystemLogs = {
    logs: [],
    total: 0,
    isLoading: false,
    isError: null,
    mutate: vi.fn(),
}

const defaultStats = { stats: null, isLoading: false, isError: null, mutate: vi.fn() }
const defaultProviders = { providers: [], isLoading: false, isError: null, mutate: vi.fn() }

beforeEach(() => {
    vi.mocked(api.useSystemLogs).mockReturnValue(defaultSystemLogs)
    vi.mocked(api.useLogStats).mockReturnValue(defaultStats)
    vi.mocked(api.useProviders).mockReturnValue(defaultProviders)
    Object.defineProperty(window, 'location', { writable: true, value: { href: '' } })
})

describe('Logs page — Request Logs error state (default tab)', () => {
    it('shows Authentication Error title when request logs API call fails', () => {
        vi.mocked(api.useLogs).mockReturnValue({
            logs: undefined,
            total: 0,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Logs />)
        expect(screen.getByText(AUTH_ERROR_TITLE)).toBeInTheDocument()
    })

    it('shows gateway token message when request logs API call fails', () => {
        vi.mocked(api.useLogs).mockReturnValue({
            logs: undefined,
            total: 0,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Logs />)
        expect(screen.getByText(AUTH_ERROR_MSG)).toBeInTheDocument()
    })

    it('shows "Go to Settings" button in error state', () => {
        vi.mocked(api.useLogs).mockReturnValue({
            logs: undefined,
            total: 0,
            isLoading: false,
            isError: new Error('Forbidden'),
            mutate: vi.fn(),
        })
        render(<Logs />)
        expect(screen.getByRole('button', { name: /go to settings/i })).toBeInTheDocument()
    })

    it('does not show error when request logs load successfully', () => {
        vi.mocked(api.useLogs).mockReturnValue({
            logs: [],
            total: 0,
            isLoading: false,
            isError: null,
            mutate: vi.fn(),
        })
        render(<Logs />)
        expect(screen.queryByText(AUTH_ERROR_TITLE)).not.toBeInTheDocument()
    })
})
