import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Spinner } from '@/components/common'
import { RequireLogin } from '@/components/RequireLogin'
import { AppLayout } from '@/layout/AppLayout'
import { VendorLayout } from '@/pages/vendor-portal/VendorLayout'

// every page is loaded only when it is first opened, so the first screen downloads much less
const CheckinPage = lazy(() => import('@/pages/checkin/PublicCheckinPage'))
const AgreementsPage = lazy(() => import('@/pages/agreements/AgreementsPage'))
const EmailsPage = lazy(() => import('@/pages/emails/EmailsPage'))
const ClientPage = lazy(() => import('@/pages/clients/ClientPage'))
const ClientsPage = lazy(() => import('@/pages/clients/ClientsPage'))
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'))
const EnquiriesPage = lazy(() => import('@/pages/enquiries/EnquiriesPage'))
const IncidentsPage = lazy(() => import('@/pages/incidents/IncidentsPage'))
const LoginPage = lazy(() => import('@/pages/login/LoginPage'))
const NotificationsPage = lazy(() => import('@/pages/notifications/NotificationsPage'))
const PublicPayPage = lazy(() => import('@/pages/pay/PublicPayPage'))
const PaymentsPage = lazy(() => import('@/pages/payments/PaymentsPage'))
const QuotationsPage = lazy(() => import('@/pages/quotations/QuotationsPage'))
const RequestDetailPage = lazy(() => import('@/pages/quotations/RequestDetailPage'))
const VendorAccountPage = lazy(() => import('@/pages/vendor-portal/VendorAccountPage'))
const VendorBookingsPage = lazy(() => import('@/pages/vendor-portal/VendorBookingsPage'))
const VendorPaymentsPage = lazy(() => import('@/pages/vendor-portal/VendorPaymentsPage'))
const VendorRequestsPage = lazy(() => import('@/pages/vendor-portal/VendorRequestsPage'))
const VendorProfilePage = lazy(() => import('@/pages/vendors/VendorProfilePage'))
const VendorsPage = lazy(() => import('@/pages/vendors/VendorsPage'))
const WeddingDetailPage = lazy(() => import('@/pages/weddings/WeddingDetailPage'))
const WeddingsPage = lazy(() => import('@/pages/weddings/WeddingsPage'))

// Only Member 1 edits this file. Every page lives in its own folder under pages/.
export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/checkin/:token" element={<CheckinPage />} />
        <Route path="/pay/:token" element={<PublicPayPage />} />
        <Route path="/vendor" element={<VendorLayout />}>
          <Route index element={<VendorBookingsPage />} />
          <Route path="requests" element={<VendorRequestsPage />} />
          <Route path="payments" element={<VendorPaymentsPage />} />
          <Route path="account" element={<VendorAccountPage />} />
        </Route>
        <Route element={<RequireLogin />}>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="enquiries" element={<EnquiriesPage />} />
            <Route path="clients" element={<ClientsPage />} />
            <Route path="clients/:id" element={<ClientPage />} />
            <Route path="weddings" element={<WeddingsPage />} />
            <Route path="weddings/:id" element={<WeddingDetailPage />} />
            <Route path="vendors" element={<VendorsPage />} />
            <Route path="vendors/:id" element={<VendorProfilePage />} />
            <Route path="quotations" element={<QuotationsPage />} />
            <Route path="quotations/:id" element={<RequestDetailPage />} />
            <Route path="incidents" element={<IncidentsPage />} />
            <Route path="payments" element={<PaymentsPage />} />
            <Route path="agreements" element={<AgreementsPage />} />
            <Route path="emails" element={<EmailsPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
          </Route>
        </Route>
      </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
