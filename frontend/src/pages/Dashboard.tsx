import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Stats {
  total: number;
  auto_passed: number;
  human_review: number;
  high_risk: number;
  missing_fields: number;
  duplicates: number;
  price_anomalies: number;
  invoice_splitting: number;
  over_limit: number;
  po_mismatches: number;
  policy_violations: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    axios.get(`${import.meta.env.VITE_API_URL}/api/dashboard/stats`)
      .then(res => setStats(res.data))
      .catch(err => console.error(err));
  }, []);

  if (!stats) return <div>Loading dashboard...</div>;

  const data = [
    { name: 'Missing Fields', count: stats.missing_fields },
    { name: 'Duplicates', count: stats.duplicates },
    { name: 'Price Anomalies', count: stats.price_anomalies },
    { name: 'Splitting', count: stats.invoice_splitting },
    { name: 'Over Limit', count: stats.over_limit },
    { name: 'PO Mismatch', count: stats.po_mismatches },
    { name: 'Policy Violation', count: stats.policy_violations },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      
      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 font-medium">Total Processed</p>
          <p className="text-3xl font-bold mt-2 text-blue-600">{stats.total}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 font-medium">Auto Passed</p>
          <p className="text-3xl font-bold mt-2 text-green-600">{stats.auto_passed}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 font-medium">Human Review</p>
          <p className="text-3xl font-bold mt-2 text-yellow-600">{stats.human_review}</p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <p className="text-sm text-gray-500 font-medium">High Risk</p>
          <p className="text-3xl font-bold mt-2 text-red-600">{stats.high_risk}</p>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 h-96">
        <h3 className="text-lg font-bold mb-4">Risk Distribution</h3>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="count" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
