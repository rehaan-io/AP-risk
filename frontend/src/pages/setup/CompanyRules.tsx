import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useConfig } from '../../ConfigContext';
import { UploadCloud, CheckCircle, Shield } from 'lucide-react';
import PoliciesDashboard from '../Policies';

const CompanyRulesSetup = () => {
  const { config, refreshConfig } = useConfig();
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<{status: string, message?: string, total?: number, current?: number} | null>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    
    // First update mode
    await axios.post(`${import.meta.env.VITE_API_URL}/api/config/policy_mode`, { policy_mode: 'COMPANY_POLICY' });
    
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/policies/upload-zip`, formData);
      const taskId = res.data.task_id;
      
      const eventSource = new EventSource(`${import.meta.env.VITE_API_URL}/api/policies/progress/${taskId}`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'start' || data.type === 'progress') {
          setProgress({ status: 'processing', current: data.processed || 0, total: data.total });
        } else if (data.type === 'complete') {
          setProgress({ status: 'complete', total: data.total });
          eventSource.close();
          setUploading(false);
          refreshConfig();
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

  const handleUseDefaults = async () => {
    setUploading(true);
    await axios.post(`${import.meta.env.VITE_API_URL}/api/config/policy_mode`, { policy_mode: 'DEFAULT_POLICY' });
    await refreshConfig();
  };

  if (config?.policy_mode !== 'PENDING') {
    return <PoliciesDashboard isSetup={true} />;
  }

  return (
    <div className="max-w-4xl mx-auto mt-10">
      <h2 className="text-3xl font-bold mb-8 text-gray-800">Company Rules Setup</h2>
      <p className="text-gray-600 mb-8 text-lg">Tell us how your company operates. We use your policies to dynamically evaluate incoming invoices.</p>
      
      <div className="grid md:grid-cols-2 gap-8">
        
        {/* Upload Custom Policies */}
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200">
          <div className="flex items-center mb-4">
            <Shield className="w-8 h-8 text-blue-600 mr-3" />
            <h3 className="text-xl font-bold">Use Company Policies</h3>
          </div>
          <p className="text-sm text-gray-500 mb-6">Upload your procurement manuals, approval matrices, and vendor rules. Our AI will automatically translate them into executable risk rules.</p>
          
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center bg-gray-50 hover:bg-gray-100 transition">
            <UploadCloud className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <input
              type="file"
              accept=".zip"
              className="hidden"
              id="policy-upload"
              onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
            />
            <label
              htmlFor="policy-upload"
              className="cursor-pointer bg-white border border-gray-300 py-2 px-4 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 inline-block mb-2"
            >
              Select ZIP File
            </label>
            {file && <p className="text-sm text-gray-600 mt-2">{file.name}</p>}
          </div>
          
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full mt-6 bg-blue-600 text-white font-bold py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? 'Processing...' : 'Upload & Extract Rules'}
          </button>
          
          {progress && progress.status === 'processing' && (
            <div className="mt-4">
              <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${(progress.current! / progress.total!) * 100}%` }}></div>
              </div>
              <p className="text-xs text-center text-gray-500">Extracting {progress.current} of {progress.total} documents...</p>
            </div>
          )}
        </div>

        {/* Use Defaults */}
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 flex flex-col">
          <div className="flex items-center mb-4">
            <CheckCircle className="w-8 h-8 text-green-600 mr-3" />
            <h3 className="text-xl font-bold">Use Default Policies</h3>
          </div>
          <p className="text-sm text-gray-500 mb-6 flex-1">Don't have your policies handy? Start with our standard enterprise defaults for price variance, limits, and PO tolerances.</p>
          
          <div className="bg-gray-50 rounded-lg p-4 mb-6 border border-gray-100">
            <ul className="text-sm space-y-2 text-gray-600 list-disc list-inside">
              <li>Requires PO above 50,000</li>
              <li>Max 10% price tolerance</li>
              <li>Max 5% total amount tolerance</li>
              <li>Flags split invoices within 7 days</li>
            </ul>
          </div>
          
          <button
            onClick={handleUseDefaults}
            disabled={uploading}
            className="w-full bg-green-600 text-white font-bold py-3 rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            Activate Default Rules
          </button>
        </div>

      </div>
    </div>
  );
};

export default CompanyRulesSetup;
