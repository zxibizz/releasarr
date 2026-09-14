import { Collapse, Group, Indicator, Select, ActionIcon } from '@mantine/core';
import { IconAdjustmentsHorizontal } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import {
  DEFAULT_SOURCE_FILTER,
  DEFAULT_SORT_FIELD,
  NATURAL_SORT_ORDER,
  SORT_FIELDS,
  type SortField,
  type SortOrder,
} from '@/features/releases/useReleaseSearch';

interface ReleaseFiltersProps {
  isMobile: boolean;
  sources: string[];
  sortField: SortField;
  setSortField: (field: SortField) => void;
  sortOrder: SortOrder;
  setSortOrder: (order: SortOrder) => void;
  sourceFilter: string;
  setSourceFilter: (source: string) => void;
  expanded: boolean;
  setExpanded: (expanded: boolean) => void;
}

export function ReleaseFilters({
  isMobile,
  sources,
  sortField,
  setSortField,
  sortOrder,
  setSortOrder,
  sourceFilter,
  setSourceFilter,
  expanded,
  setExpanded,
}: ReleaseFiltersProps) {
  const { t } = useTranslation();
  const adjusted =
    sortField !== DEFAULT_SORT_FIELD ||
    sortOrder !== NATURAL_SORT_ORDER[DEFAULT_SORT_FIELD] ||
    sourceFilter !== DEFAULT_SOURCE_FILTER;

  const controls = (
    <Group gap="sm" wrap="wrap">
      <Select
        label={t('releaseSearch.sort.label')}
        size="xs"
        w={{ base: '47%', sm: 150 }}
        allowDeselect={false}
        value={sortField}
        onChange={(value) => {
          if (!value) return;
          const field = value as SortField;
          setSortField(field);
          setSortOrder(NATURAL_SORT_ORDER[field]);
        }}
        data={SORT_FIELDS.map((field) => ({
          value: field,
          label: t(`releaseSearch.sort.fields.${field}`),
        }))}
      />
      <Select
        label={t('releaseSearch.sort.directionLabel')}
        size="xs"
        w={{ base: '47%', sm: 140 }}
        allowDeselect={false}
        value={sortOrder}
        onChange={(value) => value && setSortOrder(value as SortOrder)}
        data={[
          { value: 'desc', label: t('releaseSearch.sort.directions.desc') },
          { value: 'asc', label: t('releaseSearch.sort.directions.asc') },
        ]}
      />
      {sources.length > 0 && (
        <Select
          label={t('releaseSearch.filters.source.label')}
          size="xs"
          w={{ base: '100%', sm: 170 }}
          allowDeselect={false}
          value={sourceFilter}
          onChange={(value) => value && setSourceFilter(value)}
          data={[
            { value: DEFAULT_SOURCE_FILTER, label: t('releaseSearch.filters.source.all') },
            ...sources.map((source) => ({ value: source, label: source })),
          ]}
        />
      )}
    </Group>
  );

  if (!isMobile) return controls;

  return (
    <Collapse expanded={expanded} keepMounted={false}>
      {controls}
    </Collapse>
  );
}

interface ReleaseFiltersToggleProps {
  adjusted: boolean;
  expanded: boolean;
  setExpanded: (expanded: boolean) => void;
}

export function ReleaseFiltersToggle({
  adjusted,
  expanded,
  setExpanded,
}: ReleaseFiltersToggleProps) {
  const { t } = useTranslation();
  return (
    <Indicator disabled={!adjusted} size={8} offset={4}>
      <ActionIcon
        variant={expanded ? 'filled' : 'default'}
        size="lg"
        aria-label={t(
          adjusted ? 'releaseSearch.filters.toggleActive' : 'releaseSearch.filters.toggle',
        )}
        aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}
      >
        <IconAdjustmentsHorizontal size={18} />
      </ActionIcon>
    </Indicator>
  );
}
