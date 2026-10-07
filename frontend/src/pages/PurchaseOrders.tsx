import React, { useState, useEffect } from 'react';
import { Upload, FilePlus } from 'lucide-react';

export default function PurchaseOrders() {
  const [pos, setPos] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<{ processed: number, total: number, current: string } | null>(null);

  const fetchPOs = () => {
    fetch(`${import.meta.env.VITE_API_URL}/api/purchase-orders`)
      .then(res => res.json())
      .then(data => setPos(data))
      .catch(console.error);
  };

  useEffect(() => {
    fetchPOs();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setProgress(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/purchase-orders/upload-zip`, {
        method: 'POST',
        body: formData,
      });
      const { task_id } = await res.json();
      
      const eventSource = new EventSource(`${import.meta.env.VITE_API_URL}/api/purchase-orders/progress/${task_id}`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'start') {
          setProgress({ processed: 0, total: data.total, current: '' });
        } else if (data.type === 'progress') {
          setProgress({ processed: data.processed, total: data.total, current: data.current });
        } else if (data.type === 'complete') {
          eventSource.close();
          setUploading(false);
          setProgress(null);
          fetchPOs();
        } else if (data.type === 'error') {
          eventSource.close();
          setUploading(false);
          alert('Error: ' + data.message);
        }
      };
    } catch (err) {
      console.error(err);
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-800">Purchase Orders</h2>
        
        <label className="cursor-pointer bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 flex items-center">
          <Upload className="w-5 h-5 mr-2" />
          Upload PO ZIP
          <input type="file" className="hidden" accept=".zip" onChange={handleUpload} />
        </label>
      </div>

      {uploading && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h3 className="font-semibold mb-2">Processing ZIP...</h3>
          {progress && (
            <div>
              <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${(progress.processed / progress.total) * 100}%` }}></div>
              </div>
              <p className="text-sm text-gray-600">
                Processed {progress.processed} of {progress.total} POs. Current: {progress.current}
              </p>
            </div>
          )}
        </div>
      )}

      <div className="bg-white shadow-sm border border-gray-200 rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">PO Number</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vendor</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confidence</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {pos.map(po => (
              <tr key={po.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{po.po_number || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{po.vendor_name || 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{po.po_date ? new Date(po.po_date).toLocaleDateString() : 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{po.total_amount || 0}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{(po.extraction_confidence || 0).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
