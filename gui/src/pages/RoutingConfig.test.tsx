import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RoutingConfig } from './RoutingConfig'

vi.mock('@/lib/api', () => ({
    useRoutingConfig: vi.fn(),
    saveRoutingConfig: vi.fn(),
}))

import * as api from '@/lib/api'

const AUTH_ERROR_TITLE = 'Authentication Error'
const AUTH_ERROR_MSG =
    'Unable to load data. Your Gateway Token may be missing or invalid. Please configure your token in the Settings.'

beforeEach(() => {
    Object.defineProperty(window, 'location', { writable: true, value: { href: '' } })
})

describe('RoutingConfig page — error state', () => {
    it('shows Authentication Error title when API call fails', () => {
        vi.mocked(api.useRoutingConfig).mockReturnValue({
            routingConfig: undefined,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<RoutingConfig />)
        expect(screen.getByText(AUTH_ERROR_TITLE)).toBeInTheDocument()
    })

    it('shows gateway token missing message when API call fails', () => {
        vi.mocked(api.useRoutingConfig).mockReturnValue({
            routingConfig: undefined,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<RoutingConfig />)
        expect(screen.getByText(AUTH_ERROR_MSG)).toBeInTheDocument()
    })

    it('shows "Go to Settings" button in error state', () => {
        vi.mocked(api.useRoutingConfig).mockReturnValue({
            routingConfig: undefined,
            isLoading: false,
            isError: new Error('Forbidden'),
            mutate: vi.fn(),
        })
        render(<RoutingConfig />)
        expect(screen.getByRole('button', { name: /go to settings/i })).toBeInTheDocument()
    })
})
