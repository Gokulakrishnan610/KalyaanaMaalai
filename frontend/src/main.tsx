import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { ToastProvider } from './components/common'
import { LiveProvider } from './live/LiveProvider'
import { LoginProvider } from './login/LoginContext'
import './index.css'

const queryClient = new QueryClient({
  // data counts as fresh for 30 seconds, so going back to a screen shows it at once without asking the server again;
  // the live connection still refreshes anything that changes
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000, gcTime: 10 * 60_000 } },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <LoginProvider>
        <ToastProvider>
          <LiveProvider>
            <App />
          </LiveProvider>
        </ToastProvider>
      </LoginProvider>
    </QueryClientProvider>
  </StrictMode>,
)
