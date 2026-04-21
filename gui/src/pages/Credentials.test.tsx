import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Credentials } from './Credentials'

vi.mock('@/lib/api', () => ({
    useCredentials: vi.fn(),
    useProviders: vi.fn(),
    createCredential: vi.fn(),
    deleteCredential: vi.fn(),
    updateCredential: vi.fn(),
    verifyCredential: vi.fn(),
    getCredentialQuota: vi.fn(),
    syncProviderModels: vi.fn(),
    startOAuthFlow: vi.fn(),
    startAntigravityOAuth: vi.fn(),
}))

import * as api from '@/lib/api'

const AUTH_ERROR_TITLE = 'Authentication Error'
const AUTH_ERROR_MSG =
    'Unable to load data. Your Gateway Token may be missing or invalid. Please configure your token in the Settings.'

beforeEach(() => {
    vi.mocked(api.useProviders).mockReturnValue({ providers: [], isLoading: false, isError: null, mutate: vi.fn() })
    Object.defineProperty(window, 'location', { writable: true, value: { href: '' } })
})

describe('Credentials page — error state', () => {
    it('shows Authentication Error title when API call fails', () => {
        vi.mocked(api.useCredentials).mockReturnValue({
            credentials: undefined,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Credentials />)
        expect(screen.getByText(AUTH_ERROR_TITLE)).toBeInTheDocument()
    })

    it('shows gateway token message when API call fails', () => {
        vi.mocked(api.useCredentials).mockReturnValue({
            credentials: undefined,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Credentials />)
        expect(screen.getByText(AUTH_ERROR_MSG)).toBeInTheDocument()
    })

    it('shows "Go to Settings" button in error state', () => {
        vi.mocked(api.useCredentials).mockReturnValue({
            credentials: undefined,
            isLoading: false,
            isError: new Error('Unauthorized'),
            mutate: vi.fn(),
        })
        render(<Credentials />)
        expect(screen.getByRole('button', { name: /go to settings/i })).toBeInTheDocument()
    })

    it('does not show credentials table in error state', () => {
        vi.mocked(api.useCredentials).mockReturnValue({
            credentials: undefined,
            isLoading: false,
            isError: new Error('Forbidden'),
            mutate: vi.fn(),
        })
        render(<Credentials />)
        expect(screen.queryByRole('table')).not.toBeInTheDocument()
        expect(screen.queryByText('Add Credential')).not.toBeInTheDocument()
    })
})

describe('Credentials page — loading state', () => {
    it('shows loading indicator while fetching', () => {
        vi.mocked(api.useCredentials).mockReturnValue({
            credentials: undefined,
            isLoading: true,
            isError: null,
            mutate: vi.fn(),
        })
        render(<Credentials />)
        expect(screen.getByText(/loading credentials/i)).toBeInTheDocument()
    })
})

describe('Credentials page — success state', () => {
    it('does not show error state when data loads successfully', () => {
        vi.mocked(api.useCredentials).mockReturnValue({
            credentials: [],
            isLoading: false,
            isError: null,
            mutate: vi.fn(),
        })
        render(<Credentials />)
        expect(screen.queryByText(AUTH_ERROR_TITLE)).not.toBeInTheDocument()
    })

    it('shows "Add Credential" button when data loads', () => {
        vi.mocked(api.useCredentials).mockReturnValue({
            credentials: [],
            isLoading: false,
            isError: null,
            mutate: vi.fn(),
        })
        render(<Credentials />)
        expect(screen.getByRole('button', { name: /add credential/i })).toBeInTheDocument()
    })
})
