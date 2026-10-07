import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Shield, BookOpen, AlertTriangle, FileText, ExternalLink, Settings, Info, Tag, Check, X } from 'lucide-react';
import { useConfig } from '../ConfigContext';

export default function PolicyReview() {
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { config } = useConfig();

  const fetchRules = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/policies/rules`);
      setRules(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleAction = async (id: number, action: 'approve' | 'reject') => {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL}/api/policies/rules/${id}/${action}`);
      await fetchRules();
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading pending rules...</div>;

  const pendingRules = rules.filter(r => r.status === 'PENDING_REVIEW');
  const isSetupMode = config && !config.setup_completed;

  const renderRuleCard = (rule: any) => {
    // Formatting rule interpretations beautifully
    let interpretation = "";
    if (rule.rule_type === 'PO_REQUIRED') {
      interpretation = `Purchases above ${rule.conditions?.amount?.[">"] || rule.conditions?.amount?.value || 0} require a Purchase Order.`;
    } else if (rule.rule_type === 'TOLERANCE') {
      if (rule.conditions?.type === 'price_variance') interpretation = `Maximum allowed price variance: ${rule.action?.max_deviation_percent || 0}%`;
      else if (rule.conditions?.type === 'quantity_variance') interpretation = `Maximum allowed quantity variance: ${rule.action?.max_deviation_percent || 0}%`;
      else if (rule.conditions?.type === 'amount_variance') interpretation = `Invoice may exceed PO by maximum ${rule.action?.max_deviation_percent || 0}%`;
      else interpretation = `Tolerance rule: ${rule.action?.max_deviation_percent}%`;
    } else if (rule.rule_type === 'INVOICE_SPLITTING') {
      interpretation = `Transactions within ${rule.conditions?.aggregation_window_days || 0} days may be aggregated.`;
    } else if (rule.rule_type === 'APPROVAL_LIMIT') {
      interpretation = `Approval required for amounts > ${rule.conditions?.amount?.[">"] || rule.conditions?.amount?.value || 0}. Route to: ${rule.action?.requires_approval_from || 'Manager'}.`;
    } else {
      interpretation = "Custom condition rule.";
    }

    const hasScope = rule.scope && !rule.scope.company_wide;
    let scopeText = "";
    if (hasScope) {
      if (rule.scope.department) scopeText += `Dept: ${rule.scope.department} `;
      if (rule.scope.category) scopeText += `Cat: ${rule.scope.category} `;
      if (rule.scope.vendor) scopeText += `Vendor: ${rule.scope.vendor} `;
    }

    return (
      <div key={rule.id} className="p-6 rounded-lg border bg-white shadow-md mb-6 border-amber-300">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h4 className="font-bold text-gray-800 text-lg flex items-center">
              {rule.rule_type.replace(/_/g, ' ')}
              {hasScope && <span className="ml-3 px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full font-medium">SCOPED</span>}
            </h4>
            <p className="text-gray-900 mt-2 font-medium text-lg">{interpretation}</p>
          </div>
          
          <div className="flex space-x-3">
            <button onClick={() => handleAction(rule.id, 'reject')} className="flex items-center px-4 py-2 bg-white border border-red-200 text-red-600 rounded-lg hover:bg-red-50 font-semibold transition shadow-sm">
              <X className="w-4 h-4 mr-2" /> Reject
            </button>
            <button onClick={() => handleAction(rule.id, 'approve')} className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold transition shadow-sm">
              <Check className="w-4 h-4 mr-2" /> Approve
            </button>
          </div>
        </div>

        {hasScope && (
          <div className="mt-3 mb-3 bg-purple-50 text-purple-900 p-3 rounded-md text-sm flex items-center border border-purple-100">
            <Tag className="w-4 h-4 mr-2 text-purple-600" />
            <span className="font-semibold mr-2">Applies specifically to:</span> {scopeText}
          </div>
        )}

        {rule.exceptions && rule.exceptions.length > 0 && (
          <div className="mt-3 mb-3 bg-amber-50 p-3 rounded-md border border-amber-100">
            <h5 className="text-xs font-bold text-amber-800 uppercase mb-2 flex items-center">
              <AlertTriangle className="w-3 h-3 mr-1" /> Exceptions
            </h5>
            {rule.exceptions.map((ex: any, idx: number) => (
              <div key={idx} className="text-sm text-amber-900 mb-1">
                <strong>{ex.exception_type}:</strong> {ex.condition} 
                {ex.requires_approval_from && <span className="ml-2 text-amber-700 bg-amber-200/50 px-1.5 py-0.5 rounded text-xs">Approval: {ex.requires_approval_from}</span>}
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
          <div className="text-xs text-gray-500 flex items-center">
            <span className="flex items-center">
              Source Document • Page/Sheet {rule.source_page || 'Unknown'}
              <button className="ml-3 text-blue-600 hover:underline flex items-center">
                <ExternalLink className="w-3 h-3 mr-1" /> View Source Text
              </button>
            </span>
          </div>
          <div className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-1 rounded">
            Confidence: {(rule.confidence || 1.0) * 100}%
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto mt-4">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900">Policy Rule Review</h2>
        <p className="text-gray-600 mt-2">Please confirm the following rules extracted from your company policies.</p>
      </div>
      
      <div className="space-y-6">
        {pendingRules.map(rule => renderRuleCard(rule))}
        
        {pendingRules.length === 0 && (
          <div className="text-center py-16 bg-white rounded-xl shadow-sm border border-gray-200">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 text-green-600 mb-4">
              <Check className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">All Caught Up!</h3>
            <p className="text-gray-500 mb-8 max-w-sm mx-auto">There are no pending policy rules waiting for your review. Your company policies are fully active.</p>
            
            {isSetupMode ? (
              <button onClick={() => navigate('/setup/purchase-orders')} className="bg-blue-600 text-white px-8 py-3 rounded-lg font-bold hover:bg-blue-700 shadow-sm transition">
                Continue to Purchase Orders
              </button>
            ) : (
              <button onClick={() => navigate('/policies')} className="bg-white border border-gray-300 text-gray-700 px-8 py-3 rounded-lg font-bold hover:bg-gray-50 shadow-sm transition">
                Return to Company Rules
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
