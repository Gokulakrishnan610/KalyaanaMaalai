import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { ToastProvider } from './components/common'
import { LiveProvider } from './live/LiveProvider'
import { LoginProvider } from './login/LoginContext'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
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
