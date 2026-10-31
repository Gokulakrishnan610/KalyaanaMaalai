import { Component, lazy, Suspense, type ComponentType, type ReactNode } from 'react'
import { Card, Spinner } from '@/components/common'

/**
 * Member 3's VendorsTab and Member 4's FinanceTab are optional here. `import.meta.glob` finds the file if it
 * exists and gives an empty object if it does not, so a missing module is a placeholder card, not a crash.
 */
type TabModule = { default?: ComponentType<{ weddingId: number }>; [name: string]: unknown }
const vendorFiles = import.meta.glob<TabModule>('../vendors/VendorsTab.tsx')
const financeFiles = import.meta.glob<TabModule>('../payments/FinanceTab.tsx')

type TabComponent = ComponentType<{ weddingId: number }>

function optionalTab(files: Record<string, () => Promise<TabModule>>, exportName: string): TabComponent | null {
  const load = Object.values(files)[0]
  if (!load) return null
  return lazy<TabComponent>(async () => {
    const mod = await load()
    const found = (mod[exportName] ?? mod.default) as ComponentType<{ weddingId: number }> | undefined
    return { default: found ?? (() => <Placeholder title={exportName} /> ) }
  })
}

const VendorsTab = optionalTab(vendorFiles, 'VendorsTab')
const FinanceTab = optionalTab(financeFiles, 'FinanceTab')

export function Placeholder({ title, hint }: { title: string; hint?: string }) {
  return (
    <Card className="border-dashed text-center">
      <p className="font-medium text-slate-700">{title} is not available yet</p>
      <p className="mt-1 text-sm text-slate-500">{hint ?? 'It will appear here once that part of the project is merged.'}</p>
    </Card>
  )
}

class Catch extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}

function Slot({ Tab, title, weddingId }: { Tab: TabComponent | null; title: string; weddingId: number }) {
  const fallback = <Placeholder title={title} />
  if (!Tab) return fallback
  return (
    <Catch fallback={fallback}>
      <Suspense fallback={<Spinner />}>
        <Tab weddingId={weddingId} />
      </Suspense>
    </Catch>
  )
}

export const GuardedVendorsTab = ({ weddingId }: { weddingId: number }) => (
  <Slot Tab={VendorsTab} title="The Vendors tab" weddingId={weddingId} />
)
export const GuardedFinanceTab = ({ weddingId }: { weddingId: number }) => (
  <Slot Tab={FinanceTab} title="The Finance tab" weddingId={weddingId} />
)
export const vendorsAvailable = Boolean(VendorsTab)
export const financeAvailable = Boolean(FinanceTab)
