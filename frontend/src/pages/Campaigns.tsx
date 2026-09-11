import { Title, Card, Text, Stack, Table, Badge, Button, Group } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

interface Campaign {
  id: number;
  name: string;
  status: string;
  scheduled_at: string | null;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "gray",
  scheduled: "blue",
  sending: "orange",
  completed: "green",
  cancelled: "gray",
  failed: "red",
};

export default function Campaigns() {
  const { data, isLoading } = useQuery({
    queryKey: ["campaigns"],
    queryFn: async () => {
      const { data } = await api.get<Campaign[]>("/campaigns");
      return data;
    },
  });

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Рассылки</Title>
        <Button leftSection={<IconPlus size={16} />}>Новая рассылка</Button>
      </Group>

      <Card withBorder padding={0}>
        {isLoading ? (
          <Text p="md" c="dimmed">
            Загрузка…
          </Text>
        ) : (
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Название</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th>Запланировано</Table.Th>
                <Table.Th>Создано</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(data ?? []).map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td>{c.name}</Table.Td>
                  <Table.Td>
                    <Badge color={STATUS_COLORS[c.status] ?? "gray"}>{c.status}</Badge>
                  </Table.Td>
                  <Table.Td>
                    {c.scheduled_at ? new Date(c.scheduled_at).toLocaleString("ru-RU") : "—"}
                  </Table.Td>
                  <Table.Td>{new Date(c.created_at).toLocaleString("ru-RU")}</Table.Td>
                </Table.Tr>
              ))}
              {data?.length === 0 && (
                <Table.Tr>
                  <Table.Td colSpan={4}>
                    <Text c="dimmed" ta="center" py="lg">
                      Пока нет ни одной рассылки
                    </Text>
                  </Table.Td>
                </Table.Tr>
              )}
            </Table.Tbody>
          </Table>
        )}
      </Card>
    </Stack>
  );
}
