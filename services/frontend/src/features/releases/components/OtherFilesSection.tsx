import { Button, Collapse, Stack } from '@mantine/core';
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react';
import { useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface OtherFilesSectionProps {
  count: number;
  children: ReactNode;
}

/**
 * Subtitles, samples and NFOs are noise beside the episodes a release is opened
 * for, so they sit folded away underneath them.
 */
export function OtherFilesSection({ count, children }: OtherFilesSectionProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  if (count === 0) {
    return null;
  }

  return (
    <Stack gap="sm">
      <Button
        variant="subtle"
        color="gray"
        size="compact-sm"
        aria-expanded={expanded}
        leftSection={expanded ? <IconChevronDown size={16} /> : <IconChevronRight size={16} />}
        onClick={() => setExpanded((current) => !current)}
        style={{ alignSelf: 'flex-start' }}
      >
        {t('files.otherFiles', { defaultValue: 'Other files ({{count}})', count })}
      </Button>

      {/*
        Unmounted while closed: the mapping rows carry selects and number inputs
        that would otherwise sit in the tab order behind a collapsed section.
      */}
      <Collapse expanded={expanded} keepMounted={false}>
        <Stack gap="sm">{children}</Stack>
      </Collapse>
    </Stack>
  );
}
