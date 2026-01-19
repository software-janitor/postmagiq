import { useQuery, useMutation } from '@tanstack/react-query'
import { CreditCard, ExternalLink, FileText, Loader2 } from 'lucide-react'
import { apiGet, apiPost } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'

interface Invoice {
  id: string
  stripe_invoice_id: string
  status: string
  currency: string
  total: number
  amount_paid: number
  amount_due: number
  invoice_date: string
  paid_at: string | null
  hosted_invoice_url: string | null
  invoice_pdf: string | null
}

interface PaymentMethod {
  id: string
  type: string
  card_brand: string | null
  card_last4: string | null
  card_exp_month: number | null
  card_exp_year: number | null
  is_default: boolean
}

interface PortalResponse {
  url: string
}

export default function BillingSection() {
  const { currentWorkspaceId } = useWorkspaceStore()

  const { data: invoices, isLoading: invoicesLoading } = useQuery({
    queryKey: ['invoices', currentWorkspaceId],
    queryFn: () => apiGet<Invoice[]>(`/v1/w/${currentWorkspaceId}/billing/invoices`),
    enabled: !!currentWorkspaceId,
  })

  const { data: paymentMethods } = useQuery({
    queryKey: ['paymentMethods', currentWorkspaceId],
    queryFn: () => apiGet<PaymentMethod[]>(`/v1/w/${currentWorkspaceId}/billing/payment-methods`),
    enabled: !!currentWorkspaceId,
  })

  const portalMutation = useMutation({
    mutationFn: () =>
      apiPost<PortalResponse>(`/v1/w/${currentWorkspaceId}/billing/portal`, {
        return_url: window.location.href,
      }),
    onSuccess: (data) => {
      if (data.url) {
        window.location.href = data.url
      }
    },
  })

  const handleManageSubscription = () => {
    portalMutation.mutate()
  }

  const formatAmount = (cents: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(cents / 100)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      paid: 'bg-green-500/20 text-green-400',
      open: 'bg-amber-500/20 text-amber-400',
      draft: 'bg-zinc-500/20 text-zinc-400',
      void: 'bg-red-500/20 text-red-400',
      uncollectible: 'bg-red-500/20 text-red-400',
    }
    return styles[status] || 'bg-zinc-500/20 text-zinc-400'
  }

  return (
    <div className="space-y-6">
      {/* Payment Methods */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-amber-400" />
            <h3 className="text-lg font-semibold text-white">Payment Methods</h3>
          </div>
          <button
            onClick={handleManageSubscription}
            disabled={portalMutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {portalMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ExternalLink className="w-4 h-4" />
            )}
            Manage Subscription
          </button>
        </div>
        <div className="p-4">
          {paymentMethods && paymentMethods.length > 0 ? (
            <div className="space-y-3">
              {paymentMethods.map((pm) => (
                <div
                  key={pm.id}
                  className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-6 bg-zinc-700 rounded flex items-center justify-center text-xs font-medium text-white uppercase">
                      {pm.card_brand || pm.type}
                    </div>
                    <div>
                      <div className="text-white font-medium">
                        {pm.card_brand ? `${pm.card_brand} •••• ${pm.card_last4}` : pm.type}
                      </div>
                      {pm.card_exp_month && pm.card_exp_year && (
                        <div className="text-sm text-zinc-400">
                          Expires {pm.card_exp_month}/{pm.card_exp_year}
                        </div>
                      )}
                    </div>
                  </div>
                  {pm.is_default && (
                    <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-xs rounded">
                      Default
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 text-zinc-400">
              <CreditCard className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No payment methods on file</p>
              <p className="text-sm">Add a payment method when you upgrade</p>
            </div>
          )}
        </div>
      </div>

      {/* Invoice History */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <FileText className="w-5 h-5 text-amber-400" />
          <h3 className="text-lg font-semibold text-white">Invoice History</h3>
        </div>
        <div className="p-4">
          {invoicesLoading ? (
            <div className="text-center py-6 text-zinc-400">
              <Loader2 className="w-6 h-6 mx-auto animate-spin" />
            </div>
          ) : invoices && invoices.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-sm text-zinc-400 border-b border-zinc-800">
                    <th className="pb-3 font-medium">Date</th>
                    <th className="pb-3 font-medium">Amount</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="text-white">
                  {invoices.map((invoice) => (
                    <tr key={invoice.id} className="border-b border-zinc-800/50">
                      <td className="py-3">{formatDate(invoice.invoice_date)}</td>
                      <td className="py-3">
                        {formatAmount(invoice.total, invoice.currency)}
                      </td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusBadge(
                            invoice.status
                          )}`}
                        >
                          {invoice.status}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {invoice.hosted_invoice_url && (
                            <a
                              href={invoice.hosted_invoice_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-amber-400 hover:text-amber-300 text-sm"
                            >
                              View
                            </a>
                          )}
                          {invoice.invoice_pdf && (
                            <a
                              href={invoice.invoice_pdf}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-zinc-400 hover:text-zinc-300 text-sm"
                            >
                              PDF
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-6 text-zinc-400">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No invoices yet</p>
              <p className="text-sm">Your invoice history will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
