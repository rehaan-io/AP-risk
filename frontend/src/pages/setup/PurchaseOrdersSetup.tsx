import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useConfig } from '../../ConfigContext';
import { UploadCloud, XCircle, CheckCircle } from 'lucide-react';

const PurchaseOrdersSetup = () => {
  const { config, refreshConfig } = useConfig();
  const navigate = useNavigate();
  const [usesPo, setUsesPo] = useState<boolean | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<{status: string, message?: string, total?: number, current?: number, stats?: any} | null>(null);
  const [conflict, setConflict] = useState<boolean>(false);

  // We should ideally check if policy requires POs
  const checkConflict = async () => {
    // This could call a backend endpoint to see if any ACTIVE rules require POs
    // For now we assume no conflict or we skip the conflict check until actual invoice processing?
    // The instructions say: "The system must NOT silently ignore that policy. Instead detect the configuration conflict."
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL}/api/policies`);
      const policies = res.data;
      const requiresPo = policies.some((p: any) => p.rule_type === 'PO_REQUIRED' && p.status === 'ACTIVE');
      if (requiresPo) {
        setConflict(true);
        return true;
      }
    } catch (e) {
      console.error(e);
    }
    return false;
  };

  const handleNoPo = async () => {
    setUploading(true);
    const hasConflict = await checkConflict();
    if (hasConflict) {
      setUploading(false);
      return;
    }
    await axios.post(`${import.meta.env.VITE_API_URL}/api/config/po_mode`, { po_mode: 'NO_PO' });
    await axios.post(`${import.meta.env.VITE_API_URL}/api/config/complete`);
    await refreshConfig();
    navigate('/upload');
  };

  const handleUploadPo = async () => {
    if (!file) return;
    setUploading(true);
    
    await axios.post(`${import.meta.env.VITE_API_URL}/api/config/po_mode`, { po_mode: 'USES_PO' });
    
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/purchase-orders/upload-zip`, formData);
      const taskId = res.data.task_id;
      
      const eventSource = new EventSource(`${import.meta.env.VITE_API_URL}/api/purchase-orders/progress/${taskId}`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'start' || data.type === 'progress') {
          setProgress({ status: 'processing', current: data.processed || 0, total: data.total });
        } else if (data.type === 'complete') {
          setProgress({ status: 'complete', total: data.total, stats: data.stats });
          eventSource.close();
          setUploading(false);
        } else if (data.type === 'error') {
          setProgress({ status: 'error', message: data.message });
          eventSource.close();
          setUploading(false);
        }
      };
    } catch (e: any) {
      setProgress({ status: 'error', message: e.message });
      setUploading(false);
    }
  };

  const handleContinue = async () => {
    await axios.post(`${import.meta.env.VITE_API_URL}/api/config/complete`);
    await refreshConfig();
    navigate('/upload');
  };

  return (
    <div className="max-w-3xl mx-auto mt-10">
      <h2 className="text-3xl font-bold mb-4 text-gray-800">Purchase Order Configuration</h2>
      
      {conflict ? (
        <div className="bg-red-50 border border-red-200 p-6 rounded-lg mb-8">
          <h3 className="text-red-800 font-bold text-lg mb-2">Configuration Conflict Detected</h3>
          <p className="text-red-700 mb-4">Your company configuration says POs are not used, but an active policy requires POs for certain transactions.</p>
          <div className="flex space-x-4">
            <button onClick={() => navigate('/policies')} className="bg-white border border-red-300 text-red-700 px-4 py-2 rounded shadow-sm hover:bg-red-50">Review Policy</button>
            <button onClick={() => setConflict(false)} className="bg-red-600 text-white px-4 py-2 rounded shadow-sm hover:bg-red-700">Change PO Configuration</button>
          </div>
        </div>
      ) : null}

      {!conflict && usesPo === null && (
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 text-center">
          <h3 className="text-xl font-bold mb-6">Does your company use Purchase Orders?</h3>
          <div className="flex justify-center space-x-6">
            <button
              onClick={() => setUsesPo(true)}
              className="flex flex-col items-center p-6 border-2 border-gray-200 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition w-48"
            >
              <CheckCircle className="w-12 h-12 text-blue-600 mb-3" />
              <span className="font-bold text-gray-800 text-center">Yes, we use<br/>Purchase Orders</span>
            </button>
            
            <button
              onClick={() => handleNoPo()}
              disabled={uploading}
              className="flex flex-col items-center p-6 border-2 border-gray-200 rounded-xl hover:border-gray-500 hover:bg-gray-100 transition w-48"
            >
              <XCircle className="w-12 h-12 text-gray-500 mb-3" />
              <span className="font-bold text-gray-800 text-center">No, we do not<br/>use POs</span>
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-6 max-w-md mx-auto">
            PO-based checks will not be applied unless a company policy specifically requires a PO for a transaction.
          </p>
        </div>
      )}

      {usesPo === true && (
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200">
          <h3 className="text-xl font-bold mb-4">Upload Purchase Orders</h3>
          <p className="text-gray-600 mb-6">Upload a ZIP file containing your purchase orders (PDF, JPG, PNG). These will be used to cross-reference incoming invoices.</p>
          
          {!progress || progress.status === 'error' ? (
            <>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center bg-gray-50 mb-6">
                <UploadCloud className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <input
                  type="file"
                  accept=".zip"
                  className="hidden"
                  id="po-upload"
                  onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                />
                <label
                  htmlFor="po-upload"
                  className="cursor-pointer bg-white border border-gray-300 py-2 px-4 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 inline-block mb-2"
                >
                  Select ZIP File
                </label>
                {file && <p className="text-sm text-gray-600 mt-2">{file.name}</p>}
              </div>
              <button
                onClick={handleUploadPo}
                disabled={!file || uploading}
                className="w-full bg-blue-600 text-white font-bold py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 mb-4"
              >
                {uploading ? 'Processing...' : 'Upload POs'}
              </button>
              {progress?.status === 'error' && <p className="text-red-600 text-sm">{progress.message}</p>}
            </>
          ) : null}

          {progress && progress.status === 'processing' && (
            <div className="mt-4 text-center py-8">
              <h4 className="font-bold text-lg mb-4">Extracting Purchase Orders</h4>
              <div className="w-full bg-gray-200 rounded-full h-3 mb-2 max-w-md mx-auto">
                <div className="bg-blue-600 h-3 rounded-full transition-all" style={{ width: `${(progress.current! / progress.total!) * 100}%` }}></div>
              </div>
              <p className="text-gray-500">{progress.current} of {progress.total} processed</p>
            </div>
          )}

          {progress && progress.status === 'complete' && (
            <div className="mt-4 text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 text-green-600 mb-4">
                <CheckCircle className="w-8 h-8" />
              </div>
              <h4 className="font-bold text-2xl mb-2">Extraction Complete</h4>
              <p className="text-gray-600 mb-6">{progress.total} POs uploaded successfully.</p>
              
              <div className="flex justify-center space-x-4">
                <button onClick={() => navigate('/purchase-orders')} className="bg-white border border-gray-300 text-gray-700 px-6 py-2 rounded-lg font-semibold hover:bg-gray-50">
                  View Purchase Orders
                </button>
                <button onClick={handleContinue} className="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700">
                  Continue to Invoice Processing
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PurchaseOrdersSetup;
