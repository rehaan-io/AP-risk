import React, { useState, useEffect } from 'react';
import { AlertCircle, Clock, Eye, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import { Link } from 'react-router-dom';

export default function Exceptions() {
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExceptions();
  }, []);

  const fetchExceptions = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/invoices`);
      // Filter only exceptions
      const exceptions = res.data.filter((inv: any) => 
        inv.status === 'HUMAN_REVIEW' || inv.status === 'INFORMATION_REQUESTED'
      );
      setInvoices(exceptions);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8">Loading exceptions...</div>;

  const highRisk = invoices.filter(i => i.risk_level === 'HIGH' || i.risk_level === 'CRITICAL').length;
  const infoReq = invoices.filter(i => i.status === 'INFORMATION_REQUESTED').length;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Human Review</h2>
        <p className="text-gray-600 mt-2">Invoices flagged by the deterministic risk engine requiring manual intervention.</p>
      </div>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center text-gray-600 mb-2">
            <Clock className="w-5 h-5 mr-2" /> Pending Review
          </div>
          <div className="text-3xl font-bold text-gray-900">{invoices.length}</div>
        </div>
        
        <div className="bg-white p-6 rounded-xl shadow-sm border border-red-200">
          <div className="flex items-center text-red-600 mb-2">
            <AlertTriangle className="w-5 h-5 mr-2" /> High / Critical Risk
          </div>
          <div className="text-3xl font-bold text-red-600">{highRisk}</div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-amber-200">
          <div className="flex items-center text-amber-600 mb-2">
            <AlertCircle className="w-5 h-5 mr-2" /> Info Requested
          </div>
          <div className="text-3xl font-bold text-amber-600">{infoReq}</div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Invoice ID</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Vendor</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Risk Level</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Main Finding</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {invoices.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-gray-500">
                  No exceptions pending review. All caught up!
                </td>
              </tr>
            ) : (
              invoices.map(inv => {
                const primaryRisk = inv.risks && inv.risks.length > 0 
                  ? inv.risks.sort((a:any,b:any)=> b.score_contribution - a.score_contribution)[0]
                  : null;

                return (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-blue-600">
                      {inv.invoice_number || 'UNKNOWN'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-900">{inv.vendor_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                      {inv.currency} {inv.total_amount?.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        inv.risk_level === 'CRITICAL' ? 'bg-red-100 text-red-800' :
                        inv.risk_level === 'HIGH' ? 'bg-orange-100 text-orange-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {inv.risk_level} ({inv.risk_score})
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate">
                      {primaryRisk ? primaryRisk.reason : 'General exception'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-md text-xs ${
                        inv.status === 'INFORMATION_REQUESTED' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {inv.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link to={`/review/${inv.id}`} className="text-indigo-600 hover:text-indigo-900 flex items-center font-medium">
                        <Eye className="w-4 h-4 mr-1" /> Review
                      </Link>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
