import { Title, Text, Card, Stack, SimpleGrid, Group, Button } from "@mantine/core";
import { IconRefresh } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import { api } from "@/api/client";

export default function Dashboard() {
  const triggerSync = async () => {
    try {
      const { data } = await api.post("/clients/sync");
      notifications.show({
        color: "teal",
        title: "Синхронизация запущена",
        message: `Задача ${data.task_id}`,
      });
    } catch (err: any) {
      notifications.show({
        color: "red",
        title: "Ошибка",
        message: err?.response?.data?.detail || "Не удалось запустить синхронизацию",
      });
    }
  };

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Дашборд</Title>
        <Button leftSection={<IconRefresh size={16} />} onClick={triggerSync}>
          Синхронизировать базу
        </Button>
      </Group>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }}>
        <MetricCard title="Клиенты в базе" value="—" />
        <MetricCard title="Активные рассылки" value="—" />
        <MetricCard title="Средний скор" value="—" />
        <MetricCard title="Отправлено за месяц" value="—" />
      </SimpleGrid>

      <Card withBorder padding="lg">
        <Text c="dimmed">
          Здесь будут графики отправок, топовые рассылки и алерты. Пока пусто — подключите CRM
          в настройках и запустите синхронизацию.
        </Text>
      </Card>
    </Stack>
  );
}

function MetricCard({ title, value }: { title: string; value: string }) {
  return (
    <Card withBorder padding="md">
      <Text size="xs" c="dimmed" tt="uppercase">
        {title}
      </Text>
      <Title order={2} mt="xs">
        {value}
      </Title>
    </Card>
  );
}
