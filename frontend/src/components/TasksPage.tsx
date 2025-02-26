import React from "react";

const TasksPage: React.FC = () => {
  const triggerSyncAll = async () => {
    try {
      if (!window.confirm("Are you sure you want to trigger 'Sync all' task?"))
        return;
      const apiUrl =
        process.env.REACT_APP_BACKEND_URL ||
        `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
      const response = await fetch(`${apiUrl}/api/tasks/sync_all`, {
        method: "POST",
      });
    } catch (error) {
      console.error("Error fetching logs:", error);
    }
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-5">Tasks</h1>
      <div className="bg-gray-800 rounded-lg p-5">
        <button
          type="button"
          className="bg-blue-500 text-white py-2 px-4 rounded-lg mt-4"
          onClick={() => triggerSyncAll()}
        >
          Sync All
        </button>
      </div>
    </div>
  );
};

export default TasksPage;
