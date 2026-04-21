import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Providers } from './Providers'

vi.mock('@/lib/api', () => ({
    useProviders: vi.fn(),
    createProvider: vi.fn(),
    updateProvider: vi.fn(),
    deleteProvider: vi.fn(),
    seedProviders: vi.fn(),
    getProviderSeeds: vi.fn(),
}))

import * as api from '@/lib/api'

const AUTH_ERROR_TITLE = 'Authentication Error'
const AUTH_ERROR_MSG =
    'Unable to load data. Your Gateway Token may be missing or invalid. Please configure your token in the Settings.'

beforeEach(() => {
    Object.defineProperty(window, 'location', { writable: true, value: { href: '' } })
})

describe('Providers page — error state', () => {
    it('shows Authentication Error title when API call fails', () => {
        vi.mocked(api.useProviders).mockReturnValue({
            providers: undefined,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Providers />)
        expect(screen.getByText(AUTH_ERROR_TITLE)).toBeInTheDocument()
    })

    it('shows gateway token missing message when API call fails', () => {
        vi.mocked(api.useProviders).mockReturnValue({
            providers: undefined,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Providers />)
        expect(screen.getByText(AUTH_ERROR_MSG)).toBeInTheDocument()
    })

    it('shows "Go to Settings" button in error state', () => {
        vi.mocked(api.useProviders).mockReturnValue({
            providers: undefined,
            isLoading: false,
            isError: new Error('Forbidden'),
            mutate: vi.fn(),
        })
        render(<Providers />)
        expect(screen.getByRole('button', { name: /go to settings/i })).toBeInTheDocument()
    })
})
