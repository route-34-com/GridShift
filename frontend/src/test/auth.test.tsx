import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { json, me, mockApi } from './mockApi'

afterEach(() => {
  vi.unstubAllGlobals()
  window.history.pushState({}, '', '/')
})

describe('sign-in and access', () => {
  it('sends signed-out visitors to the sign-in page', async () => {
    mockApi({}, null)
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /forgot password/i })).toHaveAttribute('href', '/forgot-password')
  })

  it('signs in and lands on the overview', async () => {
    let signedIn = false
    mockApi({
      '/api/auth/me': () => (signedIn ? json(me('planner')) : json({ detail: 'Please sign in.' }, 401)),
      '/api/auth/login': () => {
        signedIn = true
        return json(me('planner'))
      },
    })
    render(<App />)
    await userEvent.type(await screen.findByLabelText('Email'), 'planner@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'secret-pass-1')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Saved this week')).toBeInTheDocument()
  })

  it('shows the server message for a wrong password', async () => {
    mockApi({ '/api/auth/login': () => json({ detail: 'Wrong email or password.' }, 401) }, null)
    render(<App />)
    await userEvent.type(await screen.findByLabelText('Email'), 'x@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'nope-nope-1')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Wrong email or password.')
  })

  it('opens first-time setup when no account exists', async () => {
    mockApi({ '/api/auth/setup': () => json({ needed: true, allowed: true, email: false }) }, null)
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Create the admin account' })).toBeInTheDocument()
  })

  it('hides re-plan and admin pages from viewers', async () => {
    mockApi({}, 'viewer')
    render(<App />)
    await screen.findByText('Saved this week')
    expect(screen.queryByRole('button', { name: /re-plan now/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Users' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument()
  })

  it('shows admin pages to admins', async () => {
    mockApi()
    render(<App />)
    await screen.findByText('Saved this week')
    expect(screen.getAllByRole('link', { name: 'Users' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: 'Audit log' }).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /re-plan now/i })).toBeInTheDocument()
  })

  it('reads the reset token from the link and offers a new link when it expired', async () => {
    mockApi({ '/api/auth/reset-password': () => json({ detail: 'This link has expired or was already used. Ask for a new one.' }, 400) }, null)
    window.history.pushState({}, '', '/reset#t=abc123')
    render(<App />)
    await userEvent.type(await screen.findByLabelText('New password'), 'fresh-pass-9')
    await userEvent.type(screen.getByLabelText('Confirm new password'), 'fresh-pass-9')
    await userEvent.click(screen.getByRole('button', { name: 'Set new password' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('expired')
    expect(screen.getByRole('link', { name: /request a new reset link/i })).toBeInTheDocument()
  })

  it('shows invitation details and activates the account', async () => {
    const fetchMock = mockApi(
      {
        '/api/auth/invite': () => json({ email: 'pat@example.com', name: 'Pat', role: 'planner' }),
        '/api/auth/accept-invite': () => json(me('planner')),
      },
      null,
    )
    window.history.pushState({}, '', '/invite#t=tok')
    render(<App />)
    expect(await screen.findByText('pat@example.com')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Password'), 'pat-pass-12')
    await userEvent.type(screen.getByLabelText('Confirm password'), 'pat-pass-12')
    await userEvent.click(screen.getByRole('button', { name: 'Activate account' }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/auth/accept-invite', expect.objectContaining({ method: 'POST' })))
  })

  it('confirms a forgot-password request without revealing accounts', async () => {
    mockApi({ '/api/auth/forgot-password': () => json({ message: 'If that email belongs to an active account, a reset link is on its way.' }) }, null)
    window.history.pushState({}, '', '/forgot-password')
    render(<App />)
    await userEvent.type(await screen.findByLabelText('Email'), 'who@example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Send reset link' }))
    expect(await screen.findByRole('status')).toHaveTextContent('If that email belongs')
  })
})

describe('admin pages', () => {
  it('lists users and opens the invite dialog', async () => {
    mockApi({
      '/api/users': () => json([{ id: 1, email: 'admin@example.com', name: 'Ada', role: 'admin', status: 'active', created_at: '2026-10-01T10:00:00+00:00', last_login_at: null, you: true }]),
      '/api/users/mail-status': () => json({ configured: false, host: null, sender: null }),
    })
    window.history.pushState({}, '', '/users')
    render(<App />)
    expect(await screen.findByText('admin@example.com')).toBeInTheDocument()
    expect(screen.getByText(/set up\./)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /invite user/i }))
    expect(await screen.findByRole('dialog')).toHaveTextContent('Invite a user')
  })

  it('shows audit entries with before and after details', async () => {
    mockApi({
      '/api/users': () => json([]),
      '/api/audit': () =>
        json({
          total: 1,
          entries: [
            {
              id: 7,
              at: '2026-10-02T07:00:00+00:00',
              user_id: 1,
              user_email: 'admin@example.com',
              user_name: 'Ada',
              action: 'user.update',
              outcome: 'success',
              entity: 'user',
              entity_id: '2',
              summary: 'Changed a user',
              detail: { before: { role: 'viewer' }, after: { role: 'planner' } },
              ip: '10.0.0.5',
              user_agent: 'Mozilla/5.0 (Windows NT 10.0) Chrome/130',
            },
          ],
        }),
    })
    window.history.pushState({}, '', '/audit')
    render(<App />)
    expect(await screen.findByText('Changed a user')).toBeInTheDocument()
    expect(screen.getByText('Chrome on Windows')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Changed a user'))
    expect(await screen.findByText('viewer')).toHaveClass('line-through')
    expect(screen.getByText('planner')).toBeInTheDocument()
  })

  it('sends viewers away from admin pages', async () => {
    mockApi({}, 'viewer')
    window.history.pushState({}, '', '/audit')
    render(<App />)
    expect(await screen.findByText('Saved this week')).toBeInTheDocument()
    expect(window.location.pathname).toBe('/')
  })
})
