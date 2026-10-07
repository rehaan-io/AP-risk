import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ShieldAlert, CheckCircle, XCircle, MessageSquare, RefreshCw, FileText, Bot } from 'lucide-react';

export default function InvoiceReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [explaining, setExplaining] = useState(false);
  const [infoModal, setInfoModal] = useState(false);
  const [infoText, setInfoText] = useState('');

  useEffect(() => {
    fetchInvoice();
  }, [id]);

  const fetchInvoice = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/invoices`);
      const inv = res.data.find((i: any) => i.id.toString() === id);
      setInvoice(inv);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action: 'approve' | 'reject') => {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/invoices/${id}/${action}`);
      navigate('/exceptions');
    } catch (e) {
      console.error(e);
      alert('Action failed');
    }
  };

  const handleRequestInfo = async () => {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/invoices/${id}/request-info`, { message: infoText });
      setInfoModal(false);
      fetchInvoice(); // Reload
    } catch (e) {
      console.error(e);
      alert('Failed to request info');
    }
  };

  const generateAIExplanation = async () => {
    setExplaining(true);
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/invoices/${id}/explain`);
      setInvoice({ ...invoice, ai_explanation: res.data.explanation });
    } catch (e) {
      console.error(e);
      alert('AI explanation failed (API might be overloaded). Deterministic findings are still visible below.');
    } finally {
      setExplaining(false);
    }
  };

  if (loading || !invoice) return <div className="p-8">Loading workspace...</div>;

  return (
    <div className="flex h-[calc(100vh-80px)] overflow-hidden bg-gray-50 -m-8">
      {/* LEFT PANEL - FINDINGS */}
      <div className="flex-1 overflow-y-auto p-8 border-r border-gray-200">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Invoice {invoice.invoice_number || 'UNKNOWN'}</h2>
            <p className="text-gray-500 mt-1">{invoice.vendor_name} • {invoice.currency} {invoice.total_amount?.toLocaleString()}</p>
          </div>
          <span className={`px-4 py-2 rounded-full text-sm font-bold ${
            invoice.risk_level === 'CRITICAL' ? 'bg-red-100 text-red-800' :
            invoice.risk_level === 'HIGH' ? 'bg-orange-100 text-orange-800' :
            'bg-yellow-100 text-yellow-800'
          }`}>
            {invoice.risk_level} RISK (Score: {invoice.risk_score})
          </span>
        </div>

        {/* AI Explanation Box */}
        <div className="mb-8 bg-blue-50 border border-blue-200 rounded-xl p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-semibold text-blue-900 flex items-center">
              <Bot className="w-5 h-5 mr-2" /> AI Explanation
            </h3>
            {!invoice.ai_explanation && (
              <button 
                onClick={generateAIExplanation}
                disabled={explaining}
                className="flex items-center text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {explaining ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Bot className="w-4 h-4 mr-2" />}
                Generate AI Explanation
              </button>
            )}
          </div>
          
          {invoice.ai_explanation ? (
            <p className="text-blue-800 text-sm leading-relaxed">{invoice.ai_explanation}</p>
          ) : (
            <p className="text-blue-600/70 text-sm italic">
              AI explanation is not generated automatically to save API usage. Review deterministic findings below, or generate an AI summary if needed.
            </p>
          )}
        </div>

        <h3 className="font-bold text-gray-900 mb-4 border-b pb-2">WHY WAS THIS FLAGGED?</h3>
        
        <div className="space-y-6">
          {invoice.risks?.map((risk: any) => {
            let evidenceData = null;
            try {
              evidenceData = risk.evidence ? JSON.parse(risk.evidence) : null;
            } catch(e) {}

            return (
              <div key={risk.id} className="bg-white p-5 rounded-lg shadow-sm border border-gray-200">
                <div className="flex justify-between items-start mb-3">
                  <h4 className="font-semibold text-gray-900">{risk.risk_level} — {risk.risk_type.replace(/_/g, ' ')}</h4>
                  <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    Confidence: {(risk.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                
                <p className="text-gray-700 text-sm mb-4">{risk.reason}</p>

                {evidenceData && (
                  <div className="bg-gray-50 rounded p-4 text-sm font-mono text-gray-800 border border-gray-100">
                    <div className="font-semibold text-xs text-gray-500 mb-2 uppercase">Deterministic Evidence</div>
                    <pre className="whitespace-pre-wrap">{JSON.stringify(evidenceData, null, 2)}</pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* RIGHT PANEL - AUDIT & ACTIONS */}
      <div className="w-96 bg-white flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h3 className="font-bold text-gray-900 flex items-center mb-4">
            <FileText className="w-5 h-5 mr-2 text-gray-400" /> Actions
          </h3>
          
          <div className="space-y-3">
            <button onClick={() => handleAction('approve')} className="w-full flex items-center justify-center py-2.5 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors">
              <CheckCircle className="w-5 h-5 mr-2" /> Approve
            </button>
            <button onClick={() => handleAction('reject')} className="w-full flex items-center justify-center py-2.5 px-4 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors">
              <XCircle className="w-5 h-5 mr-2" /> Reject
            </button>
            <button onClick={() => setInfoModal(true)} className="w-full flex items-center justify-center py-2.5 px-4 bg-white border-2 border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors">
              <MessageSquare className="w-5 h-5 mr-2" /> Request Information
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <h3 className="font-bold text-gray-900 mb-4">Audit History</h3>
          <div className="space-y-4">
            {invoice.logs?.sort((a:any, b:any) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()).map((log: any) => (
              <div key={log.id} className="relative pl-4 border-l-2 border-gray-200 pb-2">
                <div className="absolute w-2 h-2 bg-gray-400 rounded-full -left-[5px] top-1.5 ring-4 ring-white"></div>
                <div className="text-xs text-gray-500 mb-1">{new Date(log.timestamp).toLocaleString()}</div>
                <div className="font-medium text-sm text-gray-900">{log.action.replace(/_/g, ' ')}</div>
                {log.details && <div className="text-sm text-gray-600 mt-1">{log.details}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* REQUEST INFO MODAL */}
      {infoModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-[400px] shadow-xl">
            <h3 className="font-bold text-lg mb-4">Request Information</h3>
            <p className="text-sm text-gray-600 mb-4">What information should be requested from the submitter?</p>
            <textarea 
              className="w-full border border-gray-300 rounded-lg p-3 text-sm mb-4 h-32 focus:ring-2 focus:ring-blue-500 outline-none"
              placeholder="e.g. Please provide the revised PO or approval for the quantity variance."
              value={infoText}
              onChange={e => setInfoText(e.target.value)}
            />
            <div className="flex justify-end space-x-3">
              <button onClick={() => setInfoModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg font-medium">Cancel</button>
              <button onClick={handleRequestInfo} className="px-4 py-2 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded-lg font-medium">Send Request</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
