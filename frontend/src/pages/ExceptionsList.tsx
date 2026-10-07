import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';

export default function ExceptionsList() {
  const [invoices, setInvoices] = useState<any[]>([]);

  useEffect(() => {
    axios.get(`${import.meta.env.VITE_API_URL}/api/invoices/exceptions`)
      .then(res => setInvoices(res.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="p-6 border-b border-gray-200 flex justify-between items-center">
        <h2 className="text-xl font-bold">Exception Queue</h2>
      </div>
      
      <table className="w-full text-left text-sm text-gray-500">
        <thead className="bg-gray-50 text-gray-700">
          <tr>
            <th className="px-6 py-3">Invoice</th>
            <th className="px-6 py-3">Vendor</th>
            <th className="px-6 py-3">Amount</th>
            <th className="px-6 py-3">Risk Level</th>
            <th className="px-6 py-3">Date</th>
            <th className="px-6 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv, idx) => (
            <tr key={idx} className="border-b hover:bg-gray-50">
              <td className="px-6 py-4 font-medium text-gray-900">{inv.invoice_number || `ID: ${inv.id}`}</td>
              <td className="px-6 py-4">{inv.vendor_name || 'Unknown'}</td>
              <td className="px-6 py-4">{inv.total_amount ? `₹${inv.total_amount.toLocaleString()}` : '-'}</td>
              <td className="px-6 py-4">
                <span className={`px-2 py-1 rounded text-xs font-semibold ${
                  inv.risk_level === 'HIGH' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {inv.risk_level}
                </span>
              </td>
              <td className="px-6 py-4">{inv.invoice_date ? new Date(inv.invoice_date).toLocaleDateString() : '-'}</td>
              <td className="px-6 py-4">
                <Link to={`/invoice/${inv.id}`} className="text-blue-600 hover:underline">Review</Link>
              </td>
            </tr>
          ))}
          {invoices.length === 0 && (
            <tr>
              <td colSpan={6} className="px-6 py-8 text-center text-gray-500">No exceptions requiring review.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
