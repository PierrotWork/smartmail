import { useState } from "react";
import {
  Title,
  Stack,
  Group,
  TextInput,
  Table,
  Badge,
  Text,
  RangeSlider,
  Card,
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

interface Client {
  id: number;
  email: string;
  first_name: string | null;
  last_name: string | null;
  company: string | null;
  category: string | null;
  current_score: number | null;
  tags: string[];
}

export default function Clients() {
  const [search, setSearch] = useState("");
  const [scoreRange, setScoreRange] = useState<[number, number]>([0, 100]);

  const { data, isLoading } = useQuery({
    queryKey: ["clients", search, scoreRange],
    queryFn: async () => {
      const { data } = await api.post("/clients/search", {
        search: search || null,
        score_min: scoreRange[0],
        score_max: scoreRange[1],
      });
      return data as { items: Client[]; total: number };
    },
  });

  return (
    <Stack>
      <Title order={2}>Клиенты</Title>

      <Card withBorder padding="md">
        <Stack>
          <TextInput
            placeholder="Поиск по email, имени, компании…"
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
          />
          <div>
            <Text size="sm" mb="xs">
              Диапазон скора: {scoreRange[0]} – {scoreRange[1]}
            </Text>
            <RangeSlider
              min={0}
              max={100}
              value={scoreRange}
              onChangeEnd={setScoreRange}
              marks={[
                { value: 0, label: "0" },
                { value: 50, label: "50" },
                { value: 100, label: "100" },
              ]}
            />
          </div>
        </Stack>
      </Card>

      <Text c="dimmed">
        {isLoading ? "Загрузка…" : `Найдено: ${data?.total ?? 0}`}
      </Text>

      <Card withBorder padding={0}>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Email</Table.Th>
              <Table.Th>Имя</Table.Th>
              <Table.Th>Компания</Table.Th>
              <Table.Th>Категория</Table.Th>
              <Table.Th>Скор</Table.Th>
              <Table.Th>Теги</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(data?.items ?? []).map((c) => (
              <Table.Tr key={c.id}>
                <Table.Td>{c.email}</Table.Td>
                <Table.Td>
                  {[c.first_name, c.last_name].filter(Boolean).join(" ") || "—"}
                </Table.Td>
                <Table.Td>{c.company || "—"}</Table.Td>
                <Table.Td>{c.category || "—"}</Table.Td>
                <Table.Td>
                  {c.current_score !== null ? (
                    <Badge color={c.current_score >= 70 ? "green" : c.current_score >= 40 ? "yellow" : "gray"}>
                      {c.current_score.toFixed(0)}
                    </Badge>
                  ) : (
                    "—"
                  )}
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {c.tags.slice(0, 3).map((t) => (
                      <Badge key={t} variant="light" size="xs">
                        {t}
                      </Badge>
                    ))}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  );
}
