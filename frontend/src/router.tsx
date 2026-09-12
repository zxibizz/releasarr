import { createBrowserRouter, type LoaderFunctionArgs } from 'react-router-dom';

import AppLayout from '@/App';
import { NotFound, RouteErrorBoundary } from '@/components/RouteErrorBoundary';
import { releasesByRequestQuery } from '@/features/releases/queries';
import { RequestsPage } from '@/features/requests/pages/RequestsPage';
import { requestDetailQuery, requestsListQuery } from '@/features/requests/queries';
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
      /*
       * The list is the entry point, so it ships in the initial bundle. These two
       * carry the release search, file mapping and task tables, none of which a
       * phone should download before it needs them. Their loaders stay eager so
       * data fetching overlaps the chunk request.
       */
      {
        path: 'request/:id',
        lazy: async () => {
          const { RequestDetailPage } = await import('@/features/requests/pages/RequestDetailPage');
          return { Component: RequestDetailPage };
        },
        loader: requestDetailLoader,
        errorElement: <RouteErrorBoundary />,
      },
      {
        path: 'system/tasks',
        lazy: async () => {
          const { TasksPage } = await import('@/features/tasks/pages/TasksPage');
          return { Component: TasksPage };
        },
        errorElement: <RouteErrorBoundary />,
      },
      { path: '*', element: <NotFound /> },
    ],
  },
]);

export default router;
