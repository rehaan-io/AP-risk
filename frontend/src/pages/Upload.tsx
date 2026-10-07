import React, { useState } from 'react';
import axios from 'axios';

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress({ status: 'uploading' });

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post(`${import.meta.env.VITE_API_URL}/api/invoices/upload-zip`, formData);
      const taskId = res.data.task_id;
      
      const eventSource = new EventSource(`${import.meta.env.VITE_API_URL}/api/invoices/progress/${taskId}`);
      
      eventSource.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'start' || data.type === 'progress') {
          setProgress({
            status: 'processing',
            current: data.processed || 0,
            total: data.total,
            filename: data.current || ''
          });
        } else if (data.type === 'complete') {
          setProgress({
            status: 'complete',
            total: data.total,
            stats: data.stats
          });
          eventSource.close();
          setUploading(false);
        } else if (data.type === 'error') {
          setProgress({ status: 'error', message: data.message });
          eventSource.close();
          setUploading(false);
        }
      };
    } catch (err: any) {
      setProgress({ status: 'error', message: err.message });
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 text-center">
        <h2 className="text-2xl font-bold mb-2">BULK INVOICE ANALYZER</h2>
        <p className="text-gray-500 mb-8">Upload a ZIP file containing PDF or image invoices.</p>
        
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 mb-6 bg-gray-50">
          <input type="file" accept=".zip" onChange={handleFileChange} className="block w-full text-sm text-slate-500
      file:mr-4 file:py-2 file:px-4
      file:rounded-full file:border-0
      file:text-sm file:font-semibold
      file:bg-blue-50 file:text-blue-700
      hover:file:bg-blue-100 mx-auto" />
        </div>

        {file && (
          <div className="mb-6">
            <p className="font-medium text-gray-700">{file.name}</p>
          </div>
        )}

        <button 
          onClick={handleUpload} 
          disabled={!file || uploading}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {uploading ? 'Processing...' : 'Analyze Invoices'}
        </button>
      </div>

      {progress && progress.status === 'processing' && (
        <div className="mt-8 bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="font-bold mb-4">Processing Invoices...</h3>
          <p className="text-sm text-gray-500 mb-2">{progress.current} / {progress.total}</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
            <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${(progress.current / progress.total) * 100}%` }}></div>
          </div>
          {progress.filename && <p className="text-xs text-gray-400">Current: {progress.filename}</p>}
        </div>
      )}

      {progress && progress.status === 'complete' && (
        <div className="mt-8 bg-green-50 p-6 rounded-lg shadow-sm border border-green-200">
          <h3 className="font-bold text-green-800 mb-4">Analysis Complete</h3>
          <p className="mb-4">{progress.total} invoices processed</p>
          <ul className="space-y-1 text-sm">
            <li><strong>{progress.stats.AUTO_PASSED || 0}</strong> Auto Passed</li>
            <li><strong>{progress.stats.HUMAN_REVIEW || 0}</strong> Human Review</li>
            <li><strong>{progress.stats.HIGH_RISK || 0}</strong> High Risk</li>
            {progress.stats.FAILED > 0 && (
              <li className="text-red-600 font-semibold mt-2"><strong>{progress.stats.FAILED}</strong> Failed (Check backend terminal for Azure AI errors)</li>
            )}
          </ul>
        </div>
      )}

      {progress && progress.status === 'error' && (
        <div className="mt-8 bg-red-50 p-6 rounded-lg shadow-sm border border-red-200">
          <h3 className="font-bold text-red-800">Error Occurred</h3>
          <p className="text-sm text-red-600">{progress.message}</p>
        </div>
      )}
    </div>
  );
}
