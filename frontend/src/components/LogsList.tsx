import React, { useEffect, useState } from "react";

interface Log {
  time: string;
  level: string;
  component: string;
  message: string;
}

const LogsList: React.FC = () => {
  const [logs, setLogs] = useState<Log[]>([]);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const apiUrl =
          process.env.REACT_APP_BACKEND_URL ||
          `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
        const response = await fetch(`${apiUrl}/api/logs`);
        const data = await response.json();
        setLogs(data.records);
      } catch (error) {
        console.error("Error fetching logs:", error);
      }
    };
    fetchLogs();
  }, []);

  const formatTime = (isoTime: string): string => {
    return new Intl.DateTimeFormat(navigator.language, {
      dateStyle: "medium",
      timeStyle: "medium",
      hour12: false,
    }).format(new Date(isoTime));
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-5">Logs</h1>
      <div className="bg-gray-800 rounded-lg p-5">
        <table className="min-w-full divide-y divide-gray-700">
          <thead>
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Time
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Level
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Component
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Message
              </th>
            </tr>
          </thead>
          <tbody className="bg-gray-800 divide-y divide-gray-700">
            {logs.map((log, index) => (
              <tr key={index}>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                  {formatTime(log.time)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                  {log.level}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                  {log.component}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                  <pre>{log.message}</pre>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LogsList;
