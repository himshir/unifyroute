import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorState } from './error-state'

const AUTH_ERROR_TITLE = 'Authentication Error'
const AUTH_ERROR_MSG =
    'Unable to load data. Your Gateway Token may be missing or invalid. Please configure your token in the Settings.'

describe('ErrorState', () => {
    beforeEach(() => {
        Object.defineProperty(window, 'location', {
            writable: true,
            value: { href: '' },
        })
    })

    it('renders default Authentication Error title', () => {
        render(<ErrorState />)
        expect(screen.getByText(AUTH_ERROR_TITLE)).toBeInTheDocument()
    })

    it('renders default gateway token missing message', () => {
        render(<ErrorState />)
        expect(screen.getByText(AUTH_ERROR_MSG)).toBeInTheDocument()
    })

    it('renders custom title when provided', () => {
        render(<ErrorState title="Custom Error" />)
        expect(screen.getByText('Custom Error')).toBeInTheDocument()
        expect(screen.queryByText(AUTH_ERROR_TITLE)).not.toBeInTheDocument()
    })

    it('renders custom message when provided', () => {
        render(<ErrorState message="Something went wrong." />)
        expect(screen.getByText('Something went wrong.')).toBeInTheDocument()
        expect(screen.queryByText(AUTH_ERROR_MSG)).not.toBeInTheDocument()
    })

    it('renders "Go to Settings" button', () => {
        render(<ErrorState />)
        expect(screen.getByRole('button', { name: /go to settings/i })).toBeInTheDocument()
    })

    it('navigates to /settings when "Go to Settings" is clicked', async () => {
        const user = userEvent.setup()
        render(<ErrorState />)
        await user.click(screen.getByRole('button', { name: /go to settings/i }))
        expect(window.location.href).toBe('/settings')
    })
})
