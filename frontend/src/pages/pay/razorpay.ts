export interface CheckoutResponse {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

interface RazorpayWindow {
  Razorpay?: new (options: Record<string, unknown>) => { open: () => void }
}

const CHECKOUT_SRC = 'https://checkout.razorpay.com/v1/checkout.js'

/** Loads Razorpay's checkout script once. */
export function loadCheckout(): Promise<void> {
  if ((window as RazorpayWindow).Razorpay) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = CHECKOUT_SRC
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Could not load the payment window. Please check your internet connection and try again.'))
    document.body.appendChild(script)
  })
}

export function openCheckout(options: Record<string, unknown>): void {
  new (window as RazorpayWindow).Razorpay!(options).open()
}
