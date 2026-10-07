import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Shield, BookOpen, AlertTriangle, FileText, ExternalLink, Settings, Info, Tag } from 'lucide-react';
import { useConfig } from '../ConfigContext';
import { Link, useNavigate } from 'react-router-dom';

const Policies = ({ isSetup = false }: { isSetup?: boolean }) => {
  const [policies, setPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { config } = useConfig();

  useEffect(() => {
    fetchPolicies();
  }, []);

  const fetchPolicies = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/policies/rules`);
      setPolicies(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading company rules...</div>;

  const activeRules = policies.filter(p => p.status === 'ACTIVE');
  const pendingRules = policies.filter(p => p.status === 'PENDING_REVIEW');
  
  const renderRuleCard = (rule: any) => {
    const isDefault = rule.source_page === 'SYSTEM_DEFAULT';
    
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
      <div key={rule.id} className={`p-6 rounded-lg border bg-white shadow-sm mb-4 ${rule.status === 'PENDING_REVIEW' ? 'border-amber-300' : 'border-gray-200'}`}>
        <div className="flex justify-between items-start mb-4">
          <div>
            <h4 className="font-bold text-gray-800 text-lg flex items-center">
              {rule.rule_type.replace(/_/g, ' ')}
              {hasScope && <span className="ml-3 px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full font-medium">SCOPED</span>}
            </h4>
            <p className="text-gray-900 mt-2 font-medium text-lg">{interpretation}</p>
          </div>
          
          <div className="text-right">
            {isDefault ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                <Settings className="w-3 h-3 mr-1" /> SYSTEM DEFAULT
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                <BookOpen className="w-3 h-3 mr-1" /> COMPANY POLICY
              </span>
            )}
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
            {isDefault ? (
              <span>Source: System Standard Benchmarks</span>
            ) : (
              <span className="flex items-center">
                Source Document • Page/Sheet {rule.source_page || 'Unknown'}
                <button className="ml-3 text-blue-600 hover:underline flex items-center">
                  <ExternalLink className="w-3 h-3 mr-1" /> View Source Text
                </button>
              </span>
            )}
          </div>
          {rule.status === 'PENDING_REVIEW' && (
            <Link to="/policy-review" className="text-sm font-semibold text-amber-600 hover:text-amber-700 bg-amber-100 px-3 py-1 rounded">
              Requires Review
            </Link>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Company Rules</h2>
          <p className="text-gray-600 mt-2">Active financial rules driving risk evaluation</p>
        </div>
        <div className="flex space-x-4">
          <button 
            onClick={async () => {
              if(confirm("Are you sure you want to reset all policies and configuration?")) {
                await axios.post(`${import.meta.env.VITE_API_URL}/api/reset`);
                window.location.href = '/';
              }
            }}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 shadow-sm"
          >
            Restart Setup
          </button>
          
          {config?.policy_mode === 'DEFAULT_POLICY' && (
            <div className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg border border-gray-200 flex items-center font-medium shadow-sm">
              <Settings className="w-5 h-5 mr-2 text-gray-500" />
              Using System Default Policies
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 font-semibold uppercase tracking-wider mb-1">Policy Status</p>
          <div className="flex items-center">
            <div className={`w-3 h-3 rounded-full mr-2 ${pendingRules.length > 0 ? 'bg-amber-400' : 'bg-green-500'}`}></div>
            <p className="text-2xl font-bold text-gray-800">{pendingRules.length > 0 ? 'Review Needed' : 'Active'}</p>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 font-semibold uppercase tracking-wider mb-1">Total Rules</p>
          <p className="text-3xl font-bold text-gray-800">{policies.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 font-semibold uppercase tracking-wider mb-1">Active Rules</p>
          <p className="text-3xl font-bold text-blue-600">{activeRules.length}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-amber-200 bg-amber-50">
          <p className="text-sm text-amber-700 font-semibold uppercase tracking-wider mb-1">Pending Review</p>
          <p className="text-3xl font-bold text-amber-600">{pendingRules.length}</p>
        </div>
      </div>

      <div className="space-y-6">
        <h3 className="text-xl font-bold text-gray-800 mb-4 border-b pb-2">Key Financial Rules</h3>
        {policies.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
            <Info className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-900">No rules configured</h3>
            <p className="text-gray-500 mt-1">Configure company policies to see rules here.</p>
          </div>
        ) : (
          policies.map(rule => renderRuleCard(rule))
        )}
      </div>

      {isSetup && (
        <div className="mt-12 border-t pt-8 text-right">
          <Link to="/setup/purchase-orders" className="bg-blue-600 text-white px-8 py-3 rounded-lg font-bold hover:bg-blue-700 shadow-sm">
            Continue to Purchase Orders
          </Link>
        </div>
      )}
    </div>
  );
};

export default Policies;
