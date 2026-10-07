import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Filter, FileJson } from 'lucide-react';

export default function AuditLogs() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  
  // Filters
  const [targetId, setTargetId] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => {
    fetchLogs();
  }, [page, actionFilter]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/audit-logs`, {
        params: {
          page,
          page_size: 50,
          action: actionFilter || undefined,
          target_id: targetId || undefined
        }
      });
      setLogs(res.data.data);
      setTotalPages(res.data.total_pages);
      setTotalItems(res.data.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Audit Logs</h2>
        <p className="text-gray-600 mt-2">Complete immutable history of system events and human decisions.</p>
      </div>

      <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200 flex items-center justify-between space-x-4">
        <form onSubmit={handleSearch} className="flex-1 flex space-x-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search by ID (e.g. INV-1002)" 
              value={targetId}
              onChange={e => setTargetId(e.target.value)}
              className="pl-10 w-full border border-gray-300 rounded-lg py-2 focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          
          <select 
            value={actionFilter} 
            onChange={e => setActionFilter(e.target.value)}
            className="border border-gray-300 rounded-lg py-2 px-4 focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="">All Events</option>
            <option value="DOCUMENT_EXTRACTED">Document Extracted</option>
            <option value="RISK_DETECTED">Risk Detected</option>
            <option value="AI_EXPLANATION_GENERATED">AI Explanation Generated</option>
            <option value="HUMAN_APPROVED">Human Approved</option>
            <option value="HUMAN_REJECTED">Human Rejected</option>
            <option value="INFORMATION_REQUESTED">Information Requested</option>
          </select>

          <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700">
            Search
          </button>
        </form>
        
        <div className="text-sm text-gray-500">
          Showing {logs.length} of {totalItems} events
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Timestamp</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Event</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Entity ID</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Actor</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading && logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">Loading audit trail...</td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">No events found.</td>
              </tr>
            ) : (
              logs.map(log => <LogRow key={log.id} log={log} />)
            )}
          </tbody>
        </table>
        
        {/* Pagination Controls */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <button 
            disabled={page === 1} 
            onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">Page {page} of {totalPages || 1}</span>
          <button 
            disabled={page >= totalPages} 
            onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function LogRow({ log }: { log: any }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <React.Fragment>
      <tr className="hover:bg-gray-50 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
          {new Date(log.timestamp).toLocaleString()}
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <span className="font-medium text-gray-900">{log.action}</span>
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600 font-medium">
          {log.target_id || `ID: ${log.invoice_id}`}
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
          {log.actor}
        </td>
        <td className="px-6 py-4 text-sm text-gray-600 max-w-md truncate">
          {log.details}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-gray-50">
          <td colSpan={5} className="px-6 py-4 border-t border-gray-100">
            <div className="bg-white p-4 rounded border border-gray-200 shadow-sm text-sm font-mono text-gray-800 whitespace-pre-wrap">
              <h4 className="font-semibold text-gray-900 mb-2 font-sans flex items-center"><FileJson className="w-4 h-4 mr-2" /> Raw Event Details</h4>
              {log.details}
            </div>
          </td>
        </tr>
      )}
    </React.Fragment>
  );
}
