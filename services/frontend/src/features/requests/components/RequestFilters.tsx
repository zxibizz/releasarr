import {
  ActionIcon,
  Box,
  Button,
  Collapse,
  Group,
  Indicator,
  ScrollArea,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconAdjustmentsHorizontal, IconSearch } from '@tabler/icons-react';
import { type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import {
  DEFAULT_SORT,
  DEFAULT_STATUS,
  DEFAULT_TYPE,
  SORT_KEYS,
  STATUS_KEYS,
  TYPE_KEYS,
  type SortKey,
  type StatusFilter,
  type TypeFilter,
} from '@/features/requests/filtering';
import { useIsMobile } from '@/hooks/useIsMobile';

const FilterRow = ({ label, children }: { label: string; children: ReactNode }) => (
  <Group gap="sm" wrap="nowrap" align="center">
    <Text size="xs" c="dimmed" tt="uppercase" w={58} style={{ flexShrink: 0 }}>
      {label}
    </Text>
    <Box style={{ flex: 1, minWidth: 0 }}>{children}</Box>
  </Group>
);

function FilterPills<T extends string>({
  value,
  options,
  onSelect,
  label,
}: {
  value: T;
  options: readonly T[];
  onSelect: (key: T) => void;
  label: (key: T) => string;
}) {
  const isMobile = useIsMobile();
  const pills = (
    <Group gap="xs" wrap={isMobile ? 'nowrap' : 'wrap'} w={isMobile ? 'max-content' : undefined}>
      {options.map((key) => (
        <Button
          key={key}
          size="xs"
          radius="xl"
          variant={value === key ? 'filled' : 'default'}
          aria-pressed={value === key}
          onClick={() => onSelect(key)}
          style={{ flexShrink: 0 }}
        >
          {label(key)}
        </Button>
      ))}
    </Group>
  );

  return isMobile ? <ScrollArea type="never">{pills}</ScrollArea> : pills;
}

export interface RequestFiltersProps {
  type: TypeFilter;
  setType: (key: TypeFilter) => void;
  typeLabel: (key: TypeFilter) => string;
  status: StatusFilter;
  setStatus: (key: StatusFilter) => void;
  statusLabel: (key: StatusFilter) => string;
  search: string;
  setSearch: (value: string) => void;
  sort: SortKey;
  setSort: (value: SortKey) => void;
  /** Only callers with view_all_requests get an owner to filter by. */
  owner?: string | null;
  setOwner?: (value: string | null) => void;
  ownerOptions?: { value: string; label: string }[];
  hasWarnings: boolean;
  setHasWarnings: (value: boolean) => void;
}

export function RequestFilters({
  type,
  setType,
  typeLabel,
  status,
  setStatus,
  statusLabel,
  search,
  setSearch,
  sort,
  setSort,
  owner = null,
  setOwner,
  ownerOptions,
  hasWarnings,
  setHasWarnings,
}: RequestFiltersProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [expanded, { toggle }] = useDisclosure(false);

  const adjusted =
    type !== DEFAULT_TYPE ||
    status !== DEFAULT_STATUS ||
    sort !== DEFAULT_SORT ||
    Boolean(owner) ||
    hasWarnings;
  return (
    <Stack gap="xs">
      <Group gap="xs" wrap="nowrap" align={isMobile ? 'center' : 'flex-end'}>
        <TextInput
          label={isMobile ? undefined : t('requestsList.searchPlaceholder')}
          placeholder={t('requestsList.searchPlaceholder')}
          aria-label={t('requestsList.searchPlaceholder')}
          leftSection={isMobile ? <IconSearch size={16} /> : undefined}
          type="search"
          enterKeyHint="search"
          value={search}
          onChange={(event) => setSearch(event.currentTarget.value)}
          style={isMobile ? { flex: 1, minWidth: 0 } : undefined}
          w={isMobile ? undefined : 260}
        />
        <Indicator disabled={!adjusted} size={8} offset={4}>
          <ActionIcon
            variant={expanded ? 'filled' : 'default'}
            size="lg"
            aria-label={t(
              adjusted ? 'requestsList.filtersToggleActive' : 'requestsList.filtersToggle',
            )}
            aria-expanded={expanded}
            onClick={toggle}
          >
            <IconAdjustmentsHorizontal size={18} />
          </ActionIcon>
        </Indicator>
      </Group>
      <Collapse expanded={expanded} keepMounted={false}>
        <Stack gap="sm" pt="xs">
          <FilterRow label={t('requestsList.filters.typeLabel')}>
            <FilterPills value={type} options={TYPE_KEYS} onSelect={setType} label={typeLabel} />
          </FilterRow>
          <FilterRow label={t('requestsList.filters.statusLabel')}>
            <FilterPills
              value={status}
              options={STATUS_KEYS}
              onSelect={setStatus}
              label={statusLabel}
            />
          </FilterRow>
          <FilterRow label={t('requestsList.filters.warningsLabel')}>
            <Button
              size="xs"
              radius="xl"
              variant={hasWarnings ? 'filled' : 'default'}
              color={hasWarnings ? 'yellow' : undefined}
              aria-pressed={hasWarnings}
              onClick={() => setHasWarnings(!hasWarnings)}
            >
              {t('requestsList.filters.warningsOnly')}
            </Button>
          </FilterRow>
          {ownerOptions && setOwner ? (
            <Select
              label={t('requestsList.filters.ownerLabel')}
              placeholder={t('requestsList.filters.ownerAny')}
              clearable
              value={owner}
              onChange={setOwner}
              data={ownerOptions}
              w={{ base: '100%', sm: 200 }}
            />
          ) : null}
          <Select
            label={t('requestsList.sortAriaLabel')}
            value={sort}
            onChange={(value) => value && setSort(value as SortKey)}
            allowDeselect={false}
            data={SORT_KEYS.map((key) => ({ value: key, label: t(`requestsList.sort.${key}`) }))}
            w={{ base: '100%', sm: 200 }}
          />
        </Stack>
      </Collapse>
    </Stack>
  );
}
