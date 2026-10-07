import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { AlertCircle, CheckCircle, XCircle, FileText, FileSearch } from 'lucide-react';

export default function InvoiceDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState<any>(null);
  const [explanation, setExplanation] = useState<string>('');
  const [loadingExp, setLoadingExp] = useState<boolean>(false);
  const [role, setRole] = useState('Finance Manager');

  useEffect(() => {
    axios.get(`${import.meta.env.VITE_API_URL}/api/invoices/${id}`)
      .then(res => setInvoice(res.data))
      .catch(err => console.error(err));
  }, [id]);

  const handleAction = async (action: 'approve' | 'reject') => {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/invoices/${id}/${action}`);
      navigate('/exceptions');
    } catch (err) {
      console.error(err);
    }
  };

  const loadExplanation = async () => {
    setLoadingExp(true);
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/invoices/${id}/explain?role=${encodeURIComponent(role)}`);
      setExplanation(res.data.explanation);
    } catch (err) {
      console.error(err);
    }
    setLoadingExp(false);
  };

  if (!invoice) return <div>Loading details...</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex justify-between items-start">
        <div>
          <h2 className="text-2xl font-bold mb-1">Invoice: {invoice.invoice_number || `ID: ${invoice.id}`}</h2>
          <p className="text-gray-600">Vendor: <span className="font-medium text-gray-900">{invoice.vendor_name || 'Unknown'}</span></p>
          <p className="text-gray-600">PO Number: <span className="font-medium text-gray-900">{invoice.po_number || 'N/A'}</span></p>
          <p className="text-gray-600">Amount: <span className="font-medium text-gray-900">{invoice.total_amount?.toLocaleString() || '0'}</span></p>
          <p className="text-gray-600">Date: {invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString() : 'N/A'}</p>
        </div>
        <div className="text-right">
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold mb-2 ${
            invoice.risk_level === 'HIGH' ? 'bg-red-100 text-red-800' : 
            invoice.risk_level === 'LOW' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
          }`}>
            Risk: {invoice.risk_level}
          </span>
          <br/>
          <span className="text-sm text-gray-500">Status: {invoice.status}</span>
        </div>
      </div>

      {invoice.risks && invoice.risks.length > 0 && (
        <div className="bg-red-50 p-6 rounded-lg border border-red-200">
          <h3 className="font-bold text-red-800 mb-4 flex items-center">
            <AlertCircle className="w-5 h-5 mr-2" />
            Detected Risks
          </h3>
          <div className="space-y-4">
            {invoice.risks.map((r: any, idx: number) => (
              <div key={idx} className="bg-white p-4 rounded border border-red-100">
                <p className="font-semibold text-red-700">{r.risk_type.replace(/_/g, ' ')}</p>
                <p className="text-sm text-gray-700 mt-1">{r.reason}</p>
                {r.evidence && (
                  <div className="mt-2 text-xs bg-gray-50 p-2 rounded text-gray-600 font-mono overflow-auto whitespace-pre-wrap">
                    Evidence: {r.evidence}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-6 border-t border-red-200 pt-4">
            <h4 className="font-semibold text-gray-800 flex items-center mb-2">
              <FileSearch className="w-4 h-4 mr-2" /> Gemini Risk Explanation
            </h4>
            <div className="flex items-center space-x-2 mb-4">
              <select 
                value={role} 
                onChange={(e) => setRole(e.target.value)}
                className="border border-gray-300 rounded px-2 py-1 text-sm"
              >
                <option value="Finance Manager">Finance Manager</option>
                <option value="AP Executive">AP Executive</option>
                <option value="Auditor">Auditor</option>
              </select>
              <button onClick={loadExplanation} disabled={loadingExp} className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50">
                {loadingExp ? 'Generating...' : 'Generate Explanation'}
              </button>
            </div>
            
            {explanation && (
              <div className="bg-white p-4 rounded border border-gray-200 text-gray-800 whitespace-pre-wrap text-sm">
                {explanation}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="font-bold mb-4">Line Items</h3>
        <table className="w-full text-left text-sm text-gray-500">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2">Description</th>
              <th className="px-4 py-2">Qty</th>
              <th className="px-4 py-2">Unit Price</th>
              <th className="px-4 py-2">Amount</th>
            </tr>
          </thead>
          <tbody>
            {invoice.items?.map((item: any, idx: number) => (
              <tr key={idx} className="border-t">
                <td className="px-4 py-2">{item.description}</td>
                <td className="px-4 py-2">{item.quantity}</td>
                <td className="px-4 py-2">{item.unit_price}</td>
                <td className="px-4 py-2">{item.amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex space-x-4">
        <button onClick={() => handleAction('approve')} className="flex items-center bg-green-600 text-white px-6 py-2 rounded font-medium hover:bg-green-700">
          <CheckCircle className="w-4 h-4 mr-2" /> Approve
        </button>
        <button onClick={() => handleAction('reject')} className="flex items-center bg-red-600 text-white px-6 py-2 rounded font-medium hover:bg-red-700">
          <XCircle className="w-4 h-4 mr-2" /> Reject
        </button>
      </div>
    </div>
  );
}
