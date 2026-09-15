import { Center, Loader } from '@mantine/core';
import { createBrowserRouter, type LoaderFunctionArgs } from 'react-router-dom';

import AppLayout from '@/App';
import { NotFound, RouteErrorBoundary } from '@/components/RouteErrorBoundary';
import { RequireAuth } from '@/features/auth/components/RequireAuth';
import { RequirePermission } from '@/features/auth/components/RequirePermission';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { SetupPage } from '@/features/auth/pages/SetupPage';
import { releasesByRequestQuery } from '@/features/releases/queries';
import { RequestsPage } from '@/features/requests/pages/RequestsPage';
import { requestDetailQuery, requestsListQuery } from '@/features/requests/queries';
import { prefetchWhenOnline, queryClient } from '@/lib/queryClient';

const requestsLoader = async () => {
  await prefetchWhenOnline(() => queryClient.ensureQueryData(requestsListQuery()));
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
  await prefetchWhenOnline(async () => {
    await queryClient.ensureQueryData(requestDetailQuery(id));
    void queryClient.prefetchQuery(releasesByRequestQuery(id));
  });

  return null;
};

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage />, errorElement: <RouteErrorBoundary /> },
  { path: '/setup', element: <SetupPage />, errorElement: <RouteErrorBoundary /> },
  {
    path: '/',
    // Gates the whole shell: nothing of AppLayout mounts until a session is
    // confirmed, so a logged-out visitor never sees so much as the nav flash.
    element: <RequireAuth />,
    errorElement: <RouteErrorBoundary />,
    /*
     * Rendered while the first loader is in flight. React Router otherwise
     * shows nothing at all until it settles, which is a blank page for as long
     * as the request takes.
     */
    hydrateFallbackElement: (
      <Center mih="60vh">
        <Loader />
      </Center>
    ),
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <RequestsPage />,
            loader: requestsLoader,
            errorElement: <RouteErrorBoundary />,
          },
          /*
           * The list is the entry point, so it ships in the initial bundle. These
           * carry the release search, file mapping and task tables, none of which
           * a phone should download before it needs them. Their loaders stay
           * eager so data fetching overlaps the chunk request.
           */
          {
            path: 'request/:id',
            lazy: async () => {
              const { RequestDetailPage } =
                await import('@/features/requests/pages/RequestDetailPage');
              return { Component: RequestDetailPage };
            },
            loader: requestDetailLoader,
            errorElement: <RouteErrorBoundary />,
          },
          {
            path: 'add',
            lazy: async () => {
              const { AddRequestPage } = await import('@/features/discover/pages/AddRequestPage');
              return { Component: AddRequestPage };
            },
            errorElement: <RouteErrorBoundary />,
          },
          {
            element: <RequirePermission permission="tasks" />,
            children: [
              {
                path: 'system/tasks',
                lazy: async () => {
                  const { TasksPage } = await import('@/features/tasks/pages/TasksPage');
                  return { Component: TasksPage };
                },
                errorElement: <RouteErrorBoundary />,
              },
            ],
          },
          {
            element: <RequirePermission permission="indexers" />,
            children: [
              {
                path: 'system/indexers',
                lazy: async () => {
                  const { IndexersPage } = await import('@/features/indexers/pages/IndexersPage');
                  return { Component: IndexersPage };
                },
                errorElement: <RouteErrorBoundary />,
              },
            ],
          },
          {
            element: <RequirePermission permission="logs" />,
            children: [
              {
                path: 'system/logs',
                lazy: async () => {
                  const { LogsPage } = await import('@/features/logs/pages/LogsPage');
                  return { Component: LogsPage };
                },
                errorElement: <RouteErrorBoundary />,
              },
            ],
          },
          {
            element: <RequirePermission permission="manage_users" />,
            children: [
              {
                path: 'system/users',
                lazy: async () => {
                  const { UsersPage } = await import('@/features/users/pages/UsersPage');
                  return { Component: UsersPage };
                },
                errorElement: <RouteErrorBoundary />,
              },
            ],
          },
          { path: '*', element: <NotFound /> },
        ],
      },
    ],
  },
]);

export default router;
