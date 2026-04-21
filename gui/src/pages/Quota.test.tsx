import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Quota } from './Quota'

vi.mock('@/lib/api', () => ({
    useUsageStats: vi.fn(),
    useCredentials: vi.fn(),
    useUsageDetails: vi.fn(),
}))

import * as api from '@/lib/api'

const AUTH_ERROR_TITLE = 'Authentication Error'
const AUTH_ERROR_MSG =
    'Unable to load data. Your Gateway Token may be missing or invalid. Please configure your token in the Settings.'

beforeEach(() => {
    vi.mocked(api.useCredentials).mockReturnValue({
        credentials: [],
        isLoading: false,
        isError: null,
        mutate: vi.fn(),
    })
    vi.mocked(api.useUsageDetails).mockReturnValue({ details: null, isLoading: false, isError: null, mutate: vi.fn(), totalCost: 0, totalRequests: 0 })
    Object.defineProperty(window, 'location', { writable: true, value: { href: '' } })
})

describe('Quota page — error state', () => {
    it('shows Authentication Error title when usage stats API call fails', () => {
        vi.mocked(api.useUsageStats).mockReturnValue({
            usage: undefined,
            totalCost: 0,
            totalRequests: 0,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Quota />)
        expect(screen.getByText(AUTH_ERROR_TITLE)).toBeInTheDocument()
    })

    it('shows gateway token message when usage stats API call fails', () => {
        vi.mocked(api.useUsageStats).mockReturnValue({
            usage: undefined,
            totalCost: 0,
            totalRequests: 0,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Quota />)
        expect(screen.getByText(AUTH_ERROR_MSG)).toBeInTheDocument()
    })

    it('shows "Go to Settings" button in error state', () => {
        vi.mocked(api.useUsageStats).mockReturnValue({
            usage: undefined,
            totalCost: 0,
            totalRequests: 0,
            isLoading: false,
            isError: new Error('Forbidden'),
            mutate: vi.fn(),
        })
        render(<Quota />)
        expect(screen.getByRole('button', { name: /go to settings/i })).toBeInTheDocument()
    })

    it('does not show error when usage stats load successfully', () => {
        vi.mocked(api.useUsageStats).mockReturnValue({
            usage: [],
            totalCost: 0,
            totalRequests: 0,
            isLoading: false,
            isError: null,
            mutate: vi.fn(),
        })
        render(<Quota />)
        expect(screen.queryByText(AUTH_ERROR_TITLE)).not.toBeInTheDocument()
    })
})
