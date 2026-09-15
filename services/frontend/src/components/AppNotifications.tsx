import { Notifications } from '@mantine/notifications';

import { useIsMobile } from '@/hooks/useIsMobile';

/**
 * A right-aligned toast is conventional on desktop but collides with the burger
 * menu on a phone, where there is only room for a full-width strip.
 */
export function AppNotifications() {
  const isMobile = useIsMobile();

  // Mantine pins both of these positions to the top of the viewport, where a
  // toast would land under the status bar in a standalone iOS window.
  return (
    <Notifications
      position={isMobile ? 'top-center' : 'top-right'}
      containerWidth={isMobile ? '96vw' : 440}
      autoClose={5000}
      className="safe-area-top-fixed"
    />
  );
}
