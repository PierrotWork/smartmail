import { useEffect, useMemo, useState } from "react";
import {
  Modal,
  Stepper,
  Stack,
  TextInput,
  Textarea,
  Group,
  Button,
  Select,
  RangeSlider,
  Text,
  Card,
  Badge,
  Loader,
  Alert,
  Switch,
  MultiSelect,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

interface Template {
  id: number;
  name: string;
  subject: string;
  variables: string[];
}

interface SegmentPreview {
  total: number;
  sample: Array<{
    id: number;
    email: string;
    first_name: string | null;
    last_name: string | null;
    current_score: number | null;
  }>;
}

interface Props {
  opened: boolean;
  onClose: () => void;
}

type SegmentFilter = {
  search: string | null;
  category: string | null;
  tags_any: string[];
  score_min: number | null;
  score_max: number | null;
  include_unsubscribed: boolean;
};

const emptyFilter: SegmentFilter = {
  search: null,
  category: null,
  tags_any: [],
  score_min: 0,
  score_max: 100,
  include_unsubscribed: false,
};

export default function NewCampaignModal({ opened, onClose }: Props) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);

  // Step 1 — Basic
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [senderName, setSenderName] = useState("SmartMail");
  const [senderEmail, setSenderEmail] = useState("noreply@example.com");

  // Step 2 — Template
  const [templateId, setTemplateId] = useState<string | null>(null);

  // Step 3 — Segment
  const [filter, setFilter] = useState<SegmentFilter>(emptyFilter);

  // Step 4 — Schedule
  const [sendNow, setSendNow] = useState(true);
  const [scheduledAt, setScheduledAt] = useState<Date | null>(null);
  const [throttlePerHour, setThrottlePerHour] = useState<number | "">(0);

  // Reset when modal opens
  useEffect(() => {
    if (opened) {
      setStep(0);
      setName("");
      setDescription("");
      setSenderName("SmartMail");
      setSenderEmail("noreply@example.com");
      setTemplateId(null);
      setFilter(emptyFilter);
      setSendNow(true);
      setScheduledAt(null);
      setThrottlePerHour(0);
    }
  }, [opened]);

  // ------ Load templates for the picker ------
  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: async () => (await api.get<Template[]>("/templates")).data,
    enabled: opened,
  });

  // ------ Live segment preview (debounced) ------
  const [previewFilter, setPreviewFilter] = useState<SegmentFilter>(emptyFilter);
  useEffect(() => {
    const t = setTimeout(() => setPreviewFilter(filter), 300);
    return () => clearTimeout(t);
  }, [filter]);

  const { data: preview, isFetching: previewLoading } = useQuery({
    queryKey: ["segment-preview", previewFilter],
    queryFn: async () =>
      (await api.post<SegmentPreview>("/clients/segment-preview", previewFilter))
        .data,
    enabled: opened && step >= 2,
  });

  // ------ Create + optionally send campaign ------
  const mutation = useMutation({
    mutationFn: async () => {
      if (!templateId) throw new Error("Не выбран шаблон");
      const payload = {
        name,
        description: description || null,
        template_id: Number(templateId),
        segment_filter: filter,
        sender_name: senderName,
        sender_email: senderEmail,
        scheduled_at: sendNow ? null : scheduledAt?.toISOString() ?? null,
        throttle_per_hour: typeof throttlePerHour === "number" ? throttlePerHour : 0,
      };
      const { data: campaign } = await api.post("/campaigns", payload);

      if (sendNow) {
        await api.post(`/campaigns/${campaign.id}/send`);
      }
      return campaign;
    },
    onSuccess: (campaign) => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      notifications.show({
        color: "teal",
        title: sendNow ? "Рассылка запущена" : "Рассылка сохранена",
        message: sendNow
          ? `«${campaign.name}» отправляется получателям.`
          : `«${campaign.name}» будет отправлена в назначенное время.`,
      });
      onClose();
    },
    onError: (err: any) => {
      notifications.show({
        color: "red",
        title: "Ошибка",
        message:
          err?.response?.data?.detail ||
          err?.message ||
          "Не удалось создать рассылку",
      });
    },
  });

  // ------ Step validation ------
  const canGoNext = useMemo(() => {
    if (step === 0) return name.trim() && senderName.trim() && /@/.test(senderEmail);
    if (step === 1) return !!templateId;
    if (step === 2) return (preview?.total ?? 0) > 0;
    if (step === 3) return sendNow || !!scheduledAt;
    return true;
  }, [step, name, senderName, senderEmail, templateId, preview, sendNow, scheduledAt]);

  const selectedTemplate = templates?.find((t) => String(t.id) === templateId);

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="xl"
      title="Новая рассылка"
      centered
    >
      <Stepper active={step} onStepClick={setStep} allowNextStepsSelect={false}>
        {/* ============ ШАГ 1: ОСНОВНОЕ ============ */}
        <Stepper.Step label="Основное" description="Название и отправитель">
          <Stack mt="md">
            <TextInput
              label="Название рассылки"
              placeholder="Промо-акция, июньская подборка…"
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
              required
            />
            <Textarea
              label="Описание (внутреннее)"
              placeholder="Для чего эта рассылка, зачем сделана"
              value={description}
              onChange={(e) => setDescription(e.currentTarget.value)}
              autosize
              minRows={2}
            />
            <Group grow>
              <TextInput
                label="Имя отправителя"
                value={senderName}
                onChange={(e) => setSenderName(e.currentTarget.value)}
                required
              />
              <TextInput
                label="Email отправителя"
                type="email"
                value={senderEmail}
                onChange={(e) => setSenderEmail(e.currentTarget.value)}
                required
              />
            </Group>
          </Stack>
        </Stepper.Step>

        {/* ============ ШАГ 2: ШАБЛОН ============ */}
        <Stepper.Step label="Шаблон" description="Что отправляем">
          <Stack mt="md">
            <Select
              label="Шаблон письма"
              placeholder={
                templates?.length ? "Выбери шаблон" : "Шаблонов ещё нет — создай через API"
              }
              data={
                templates?.map((t) => ({
                  value: String(t.id),
                  label: `${t.name} — ${t.subject}`,
                })) ?? []
              }
              value={templateId}
              onChange={setTemplateId}
              searchable
              nothingFoundMessage="Ничего не нашлось"
            />
            {selectedTemplate && (
              <Card withBorder padding="sm">
                <Text size="sm" c="dimmed" mb="xs">
                  Тема письма
                </Text>
                <Text fw={500}>{selectedTemplate.subject}</Text>
                {selectedTemplate.variables.length > 0 && (
                  <>
                    <Text size="sm" c="dimmed" mt="md" mb="xs">
                      Переменные подстановки
                    </Text>
                    <Group gap="xs">
                      {selectedTemplate.variables.map((v) => (
                        <Badge key={v} variant="light">
                          {"{{ " + v + " }}"}
                        </Badge>
                      ))}
                    </Group>
                  </>
                )}
              </Card>
            )}
            {templates?.length === 0 && (
              <Alert color="yellow" title="Нет ни одного шаблона">
                Создай хотя бы один шаблон через{" "}
                <a href="/docs" target="_blank" rel="noreferrer">
                  Swagger
                </a>{" "}
                (эндпойнт POST /api/v1/templates) или запусти
                <code style={{ padding: "0 4px" }}>
                  seed_dev_data.py
                </code>{" "}
                — он засеет 3 демо-шаблона.
              </Alert>
            )}
          </Stack>
        </Stepper.Step>

        {/* ============ ШАГ 3: АУДИТОРИЯ ============ */}
        <Stepper.Step label="Аудитория" description="Кому отправляем">
          <Stack mt="md">
            <TextInput
              label="Поиск"
              placeholder="Email, имя, компания"
              value={filter.search ?? ""}
              onChange={(e) =>
                setFilter((f) => ({ ...f, search: e.currentTarget.value || null }))
              }
            />
            <TextInput
              label="Категория (opf/тип)"
              placeholder="vip, enterprise, ООО…"
              value={filter.category ?? ""}
              onChange={(e) =>
                setFilter((f) => ({ ...f, category: e.currentTarget.value || null }))
              }
            />
            <MultiSelect
              label="Теги (любой из)"
              placeholder="paying, engaged, recent-purchase…"
              data={filter.tags_any}
              value={filter.tags_any}
              onChange={(v) => setFilter((f) => ({ ...f, tags_any: v }))}
              searchable
              clearable
            />
            <div>
              <Text size="sm" fw={500} mb="xs">
                Диапазон скора: {filter.score_min ?? 0} — {filter.score_max ?? 100}
              </Text>
              <RangeSlider
                min={0}
                max={100}
                value={[filter.score_min ?? 0, filter.score_max ?? 100]}
                onChangeEnd={([mn, mx]) =>
                  setFilter((f) => ({ ...f, score_min: mn, score_max: mx }))
                }
                marks={[
                  { value: 0, label: "0" },
                  { value: 50, label: "50" },
                  { value: 100, label: "100" },
                ]}
              />
            </div>
            <Switch
              label="Включать отписавшихся"
              checked={filter.include_unsubscribed}
              onChange={(e) =>
                setFilter((f) => ({
                  ...f,
                  include_unsubscribed: e.currentTarget.checked,
                }))
              }
            />

            <Card withBorder padding="sm">
              <Group justify="space-between" mb="xs">
                <Text fw={500}>Получателей в сегменте</Text>
                {previewLoading ? (
                  <Loader size="xs" />
                ) : (
                  <Badge
                    color={preview && preview.total > 0 ? "teal" : "gray"}
                    size="lg"
                  >
                    {preview?.total ?? 0}
                  </Badge>
                )}
              </Group>
              {preview && preview.sample.length > 0 && (
                <>
                  <Text size="xs" c="dimmed" mb="xs">
                    Пример:
                  </Text>
                  <Stack gap={4}>
                    {preview.sample.map((c) => (
                      <Text key={c.id} size="sm">
                        {c.email}
                        {(c.first_name || c.last_name) &&
                          ` — ${[c.first_name, c.last_name].filter(Boolean).join(" ")}`}
                        {c.current_score !== null && (
                          <Badge size="xs" ml="xs" variant="light">
                            {c.current_score.toFixed(0)}
                          </Badge>
                        )}
                      </Text>
                    ))}
                  </Stack>
                </>
              )}
              {preview && preview.total === 0 && (
                <Text size="sm" c="dimmed">
                  Никто не попадает под фильтры. Ослабь условия или засей клиентов.
                </Text>
              )}
            </Card>
          </Stack>
        </Stepper.Step>

        {/* ============ ШАГ 4: ОТПРАВКА ============ */}
        <Stepper.Step label="Отправка" description="Когда и как">
          <Stack mt="md">
            <Switch
              label="Отправить сразу"
              checked={sendNow}
              onChange={(e) => setSendNow(e.currentTarget.checked)}
            />
            {!sendNow && (
              <DateTimePicker
                label="Запланировать на"
                placeholder="Выбери дату и время"
                value={scheduledAt}
                onChange={setScheduledAt}
                minDate={new Date()}
                required
              />
            )}
            <TextInput
              label="Ограничение скорости (писем/час, 0 = без лимита)"
              type="number"
              value={throttlePerHour}
              onChange={(e) => {
                const v = e.currentTarget.value;
                setThrottlePerHour(v === "" ? "" : Number(v));
              }}
            />

            {/* Ревью */}
            <Card withBorder padding="md" bg="dark.6">
              <Text fw={600} mb="sm">
                Итог
              </Text>
              <Stack gap={6}>
                <Row k="Название" v={name} />
                <Row k="Отправитель" v={`${senderName} <${senderEmail}>`} />
                <Row k="Шаблон" v={selectedTemplate?.name ?? "—"} />
                <Row k="Получателей" v={String(preview?.total ?? 0)} />
                <Row
                  k="Когда"
                  v={
                    sendNow
                      ? "Сразу после нажатия «Отправить»"
                      : scheduledAt
                        ? scheduledAt.toLocaleString("ru-RU")
                        : "—"
                  }
                />
              </Stack>
            </Card>
          </Stack>
        </Stepper.Step>

        <Stepper.Completed>
          <Text ta="center" mt="xl">
            Готово ✅
          </Text>
        </Stepper.Completed>
      </Stepper>

      {/* ============ FOOTER ============ */}
      <Group justify="space-between" mt="xl">
        <Button
          variant="default"
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
        >
          Назад
        </Button>
        {step < 3 ? (
          <Button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canGoNext}
          >
            Далее
          </Button>
        ) : (
          <Button
            color={sendNow ? "teal" : "indigo"}
            onClick={() => mutation.mutate()}
            loading={mutation.isPending}
            disabled={!canGoNext}
          >
            {sendNow ? "Отправить сейчас" : "Запланировать"}
          </Button>
        )}
      </Group>
    </Modal>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <Group gap="sm">
      <Text size="sm" c="dimmed" w={120}>
        {k}:
      </Text>
      <Text size="sm">{v}</Text>
    </Group>
  );
}
