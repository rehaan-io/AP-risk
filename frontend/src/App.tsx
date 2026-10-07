import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Exceptions from './pages/Exceptions';
import InvoiceReview from './pages/InvoiceReview';
import AuditLogs from './pages/AuditLogs';
import PurchaseOrders from './pages/PurchaseOrders';
import Policies from './pages/Policies';
import PolicyReview from './pages/PolicyReview';
import CompanyRulesSetup from './pages/setup/CompanyRules';
import PurchaseOrdersSetup from './pages/setup/PurchaseOrdersSetup';
import { ConfigProvider, useConfig } from './ConfigContext';
import { LayoutDashboard, UploadCloud, AlertCircle, ShoppingCart, FileText, CheckSquare, Lock, Activity } from 'lucide-react';

const AppContent = () => {
  const { config, loading } = useConfig();
  const location = useLocation();

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500">Loading Configuration...</div>;
  }

  const isSetupIncomplete = config && !config.setup_completed;

  // Determine paths based on state
  const policiesPath = isSetupIncomplete ? '/setup/company-rules' : '/policies';
  const poPath = isSetupIncomplete ? '/setup/purchase-orders' : '/purchase-orders';

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Unified Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6">
          <h1 className="text-xl font-bold text-gray-800 tracking-tight">AP Risk Intelligence</h1>
        </div>
        
        <nav className="px-4 py-2 space-y-1 flex-1">
          <div className="px-4 py-2 mt-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Configuration
          </div>
          
          <Link to={policiesPath} className={`flex items-center px-4 py-2 rounded-md transition-colors ${location.pathname.includes('policies') || location.pathname.includes('company-rules') ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-gray-700 hover:bg-gray-100'}`}>
            <FileText className="w-5 h-5 mr-3" />
            Company Rules
            {config?.policy_mode !== 'PENDING' && <span className="ml-auto text-blue-600">✓</span>}
          </Link>
          
          <Link 
            to={poPath} 
            className={`flex items-center px-4 py-2 rounded-md transition-colors ${location.pathname.includes('purchase-orders') ? 'bg-blue-50 text-blue-700 font-semibold' : (config?.policy_mode === 'PENDING' ? 'text-gray-400 cursor-not-allowed' : 'text-gray-700 hover:bg-gray-100')}`}
            onClick={(e) => config?.policy_mode === 'PENDING' && e.preventDefault()}
          >
            <ShoppingCart className="w-5 h-5 mr-3" />
            Purchase Orders
            {config?.po_mode !== 'PENDING' && <span className="ml-auto text-blue-600">✓</span>}
          </Link>

          <Link to="/policy-review" className={`flex items-center px-4 py-2 rounded-md transition-colors ${location.pathname === '/policy-review' ? 'bg-blue-50 text-blue-700 font-semibold' : (config?.policy_mode === 'PENDING' ? 'text-gray-400 cursor-not-allowed' : 'text-gray-700 hover:bg-gray-100')}`} onClick={(e) => config?.policy_mode === 'PENDING' && e.preventDefault()}>
            <CheckSquare className="w-5 h-5 mr-3" />
            Policy Review
          </Link>

          <div className="px-4 py-4 mt-4 text-xs font-semibold text-gray-400 uppercase tracking-wider border-t border-gray-100">
            Operations
          </div>

          {isSetupIncomplete ? (
            <>
              <div className="flex items-center px-4 py-2 text-gray-400 cursor-not-allowed">
                <LayoutDashboard className="w-5 h-5 mr-3 opacity-50" />
                <span className="flex-1">Dashboard</span>
                <Lock className="w-4 h-4 opacity-50" />
              </div>
              <div className="flex items-center px-4 py-2 text-gray-400 cursor-not-allowed">
                <UploadCloud className="w-5 h-5 mr-3 opacity-50" />
                <span className="flex-1">Upload Invoices</span>
                <Lock className="w-4 h-4 opacity-50" />
              </div>
              <div className="flex items-center px-4 py-2 text-gray-400 cursor-not-allowed">
                <AlertCircle className="w-5 h-5 mr-3 opacity-50" />
                <span className="flex-1">Exceptions</span>
                <Lock className="w-4 h-4 opacity-50" />
              </div>
            </>
          ) : (
            <>
              <Link to="/" className={`flex items-center px-4 py-2 rounded-md transition-colors ${location.pathname === '/' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-gray-700 hover:bg-gray-100'}`}>
                <LayoutDashboard className="w-5 h-5 mr-3" />
                Dashboard
              </Link>
              <Link to="/upload" className={`flex items-center px-4 py-2 rounded-md transition-colors ${location.pathname === '/upload' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-gray-700 hover:bg-gray-100'}`}>
                <UploadCloud className="w-5 h-5 mr-3" />
                Upload Invoices
              </Link>
              <Link to="/exceptions" className={`flex items-center px-4 py-2 rounded-md transition-colors ${location.pathname === '/exceptions' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-gray-700 hover:bg-gray-100'}`}>
                <AlertCircle className="w-5 h-5 mr-3" />
                Exceptions
              </Link>
              <Link to="/audit-logs" className={`flex items-center px-4 py-2 rounded-md transition-colors ${location.pathname === '/audit-logs' ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-gray-700 hover:bg-gray-100'}`}>
                <Activity className="w-5 h-5 mr-3" />
                Audit Logs
              </Link>
            </>
          )}
        </nav>
      </aside>

      <main className="flex-1 p-8 overflow-auto">
        <Routes>
          {isSetupIncomplete ? (
            <>
              <Route path="/setup/company-rules" element={<CompanyRulesSetup />} />
              <Route path="/setup/purchase-orders" element={<PurchaseOrdersSetup />} />
              <Route path="/policy-review" element={<PolicyReview />} />
              {/* Redirect anything else to the correct setup step */}
              <Route path="*" element={<Navigate to={config?.policy_mode === 'PENDING' ? '/setup/company-rules' : '/setup/purchase-orders'} replace />} />
            </>
          ) : (
            <>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/purchase-orders" element={<PurchaseOrders />} />
              <Route path="/policies" element={<Policies />} />
              <Route path="/policy-review" element={<PolicyReview />} />
              <Route path="/exceptions" element={<Exceptions />} />
              <Route path="/review/:id" element={<InvoiceReview />} />
              <Route path="/audit-logs" element={<AuditLogs />} />
              <Route path="/setup/*" element={<Navigate to="/" replace />} />
            </>
          )}
        </Routes>
      </main>
    </div>
  );
};

function App() {
  return (
    <ConfigProvider>
      <Router>
        <AppContent />
      </Router>
    </ConfigProvider>
  );
}

export default App;
