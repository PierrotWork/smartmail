import { useMemo, useState } from "react";
import {
  Title,
  Stack,
  Card,
  Text,
  TextInput,
  PasswordInput,
  NumberInput,
  Select,
  Button,
  Group,
  Badge,
  Tabs,
  Alert,
  ActionIcon,
  Tooltip,
} from "@mantine/core";
import {
  IconKey,
  IconMail,
  IconRobot,
  IconRefresh,
  IconRotateClockwise,
  IconInfoCircle,
} from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { api } from "@/api/client";

interface SettingItem {
  key: string;
  section: "api_keys" | "email" | "olm";
  section_title: string;
  label: string;
  kind: "string" | "password" | "number" | "select";
  choices: string[] | null;
  secret: boolean;
  help: string | null;
  value: string | null;
  is_overridden: boolean;
  has_env_default: boolean;
}

const SECTIONS = [
  { key: "api_keys", title: "API-ключи", icon: IconKey },
  { key: "email", title: "Отправитель писем", icon: IconMail },
  { key: "olm", title: "OLM keys", icon: IconRobot },
];

export default function Settings() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string | null>("api_keys");

  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: async () => (await api.get<SettingItem[]>("/settings")).data,
  });

  const grouped = useMemo(() => {
    const map: Record<string, SettingItem[]> = {};
    (data ?? []).forEach((item) => {
      (map[item.section] ??= []).push(item);
    });
    return map;
  }, [data]);

  const mutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string | null }) =>
      (await api.put<SettingItem>(`/settings/${key}`, { value })).data,
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      notifications.show({
        color: "teal",
        title: "Сохранено",
        message: updated.label,
        autoClose: 2000,
      });
    },
    onError: (err: any) => {
      notifications.show({
        color: "red",
        title: "Ошибка",
        message: err?.response?.data?.detail ?? String(err),
      });
    },
  });

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Настройки</Title>
        <Button
          variant="subtle"
          leftSection={<IconRefresh size={16} />}
          onClick={() => queryClient.invalidateQueries({ queryKey: ["settings"] })}
        >
          Обновить
        </Button>
      </Group>

      <Alert color="blue" icon={<IconInfoCircle size={16} />}>
        Значения переопределяют то, что задано в <code>.env</code>. Пустое поле =
        удалить override (вернётся значение из .env). Секреты маскируются — введи
        новое значение полностью, чтобы поменять.
      </Alert>

      {isLoading && <Text c="dimmed">Загрузка…</Text>}

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List>
          {SECTIONS.map(({ key, title, icon: Icon }) => (
            <Tabs.Tab key={key} value={key} leftSection={<Icon size={16} />}>
              {title}
            </Tabs.Tab>
          ))}
        </Tabs.List>

        {SECTIONS.map(({ key: sectionKey, title }) => (
          <Tabs.Panel key={sectionKey} value={sectionKey} pt="md">
            <Stack>
              {(grouped[sectionKey] ?? []).map((item) => (
                <SettingRow
                  key={item.key}
                  item={item}
                  onSave={(v) => mutation.mutate({ key: item.key, value: v })}
                  onReset={() => mutation.mutate({ key: item.key, value: null })}
                />
              ))}
              {(grouped[sectionKey] ?? []).length === 0 && (
                <Text c="dimmed" ta="center" py="xl">
                  В разделе «{title}» пока пусто.
                </Text>
              )}
            </Stack>
          </Tabs.Panel>
        ))}
      </Tabs>
    </Stack>
  );
}

function SettingRow({
  item,
  onSave,
  onReset,
}: {
  item: SettingItem;
  onSave: (value: string) => void;
  onReset: () => void;
}) {
  const [draft, setDraft] = useState<string>("");
  const [showEditor, setShowEditor] = useState(false);

  const displayCurrent = item.value ?? (item.has_env_default ? "(env-default)" : "—");

  return (
    <Card withBorder padding="md">
      <Group justify="space-between" wrap="nowrap" align="flex-start">
        <div style={{ flex: 1 }}>
          <Group gap="xs">
            <Text fw={500}>{item.label}</Text>
            {item.is_overridden && (
              <Badge size="xs" color="indigo" variant="light">
                override
              </Badge>
            )}
            {!item.is_overridden && item.has_env_default && (
              <Badge size="xs" color="gray" variant="light">
                из .env
              </Badge>
            )}
            {item.secret && (
              <Badge size="xs" color="orange" variant="light">
                секрет
              </Badge>
            )}
          </Group>
          <Text size="xs" c="dimmed" mt={4}>
            {item.key}
          </Text>
          {item.help && (
            <Text size="xs" c="dimmed" mt={2}>
              {item.help}
            </Text>
          )}
          <Text size="sm" mt="xs" ff="monospace" c={item.value ? undefined : "dimmed"}>
            {displayCurrent}
          </Text>
        </div>

        <Group gap="xs">
          {item.is_overridden && (
            <Tooltip label="Сбросить override (вернуться к .env)">
              <ActionIcon
                variant="subtle"
                color="gray"
                onClick={() => {
                  if (confirm("Сбросить и вернуться к значению из .env?")) onReset();
                }}
              >
                <IconRotateClockwise size={16} />
              </ActionIcon>
            </Tooltip>
          )}
          <Button
            variant={showEditor ? "filled" : "light"}
            size="xs"
            onClick={() => {
              setShowEditor((s) => !s);
              setDraft("");
            }}
          >
            {showEditor ? "Отмена" : "Изменить"}
          </Button>
        </Group>
      </Group>

      {showEditor && (
        <Group mt="md" align="flex-end" wrap="nowrap">
          <div style={{ flex: 1 }}>
            {item.kind === "select" && item.choices ? (
              <Select
                label="Новое значение"
                data={item.choices}
                value={draft || null}
                onChange={(v) => setDraft(v ?? "")}
              />
            ) : item.kind === "password" ? (
              <PasswordInput
                label="Новое значение"
                value={draft}
                onChange={(e) => setDraft(e.currentTarget.value)}
                placeholder="Вставь новый ключ полностью"
              />
            ) : item.kind === "number" ? (
              <NumberInput
                label="Новое значение"
                value={draft ? Number(draft) : ""}
                onChange={(v) => setDraft(v === "" ? "" : String(v))}
              />
            ) : (
              <TextInput
                label="Новое значение"
                value={draft}
                onChange={(e) => setDraft(e.currentTarget.value)}
              />
            )}
          </div>
          <Button
            onClick={() => {
              if (!draft) return;
              onSave(draft);
              setShowEditor(false);
              setDraft("");
            }}
            disabled={!draft}
          >
            Сохранить
          </Button>
        </Group>
      )}
    </Card>
  );
}
