import { createBrowserRouter, type LoaderFunctionArgs } from 'react-router-dom';

import AppLayout from '@/App';
import { NotFound } from '@/components/NotFound';
import { RequestsList } from '@/components/RequestsList';
import RouteErrorBoundary from '@/components/RouteErrorBoundary';
import { RequestPage } from '@/features/requests/RequestPage';
import { queryClient } from '@/lib/queryClient';
import { releasesKeys, requestsKeys } from '@/lib/queryKeys';
import { fetchRequest, fetchRequests, fetchReleasesByRequest } from '@/services/api';

export const requestsLoader = async () => {
  await queryClient.ensureQueryData({
    queryKey: requestsKeys.list(undefined),
    queryFn: () => fetchRequests(),
  });

  return null;
};

export const requestDetailLoader = async ({ params }: LoaderFunctionArgs) => {
  const { id } = params;

  if (!id) {
    throw new Response('Request identifier is required.', { status: 400, statusText: 'Bad Request' });
  }

  await Promise.all([
    queryClient.ensureQueryData({
      queryKey: requestsKeys.detail(id),
      queryFn: () => fetchRequest(id),
    }),
    queryClient.ensureQueryData({
      queryKey: releasesKeys.byRequest(id),
      queryFn: () => fetchReleasesByRequest(id),
    }),
  ]);

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
        element: <RequestsList />,
        loader: requestsLoader,
        errorElement: <RouteErrorBoundary />,
      },
      {
        path: 'request/:id',
        element: <RequestPage />,
        loader: requestDetailLoader,
        errorElement: <RouteErrorBoundary />,
      },
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
]);

export default router;
