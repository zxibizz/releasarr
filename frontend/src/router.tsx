import { createBrowserRouter, type LoaderFunctionArgs } from 'react-router-dom';

import AppLayout from '@/App';
import { NotFound, RouteErrorBoundary } from '@/components/RouteErrorBoundary';
import { releasesByRequestQuery } from '@/features/releases/queries';
import { RequestDetailPage } from '@/features/requests/pages/RequestDetailPage';
import { RequestsPage } from '@/features/requests/pages/RequestsPage';
import { requestDetailQuery, requestsListQuery } from '@/features/requests/queries';
import { TasksPage } from '@/features/tasks/pages/TasksPage';
import { queryClient } from '@/lib/queryClient';

const requestsLoader = async () => {
  await queryClient.ensureQueryData(requestsListQuery());
  return null;
};

const requestDetailLoader = async ({ params }: LoaderFunctionArgs) => {
  const { id } = params;
  if (!id) {
    throw new Response('Request identifier is required.', {
      status: 400,
      statusText: 'Bad Request',
    });
  }

  // The detail must resolve (it drives the page); releases can arrive later.
  await queryClient.ensureQueryData(requestDetailQuery(id));
  void queryClient.prefetchQuery(releasesByRequestQuery(id));

  return null;
};

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        index: true,
        element: <RequestsPage />,
        loader: requestsLoader,
        errorElement: <RouteErrorBoundary />,
      },
      {
        path: 'request/:id',
        element: <RequestDetailPage />,
        loader: requestDetailLoader,
        errorElement: <RouteErrorBoundary />,
      },
      {
        path: 'system/tasks',
        element: <TasksPage />,
        errorElement: <RouteErrorBoundary />,
      },
      { path: '*', element: <NotFound /> },
    ],
  },
]);

export default router;
