import { Title, Card, Text, Stack } from "@mantine/core";

export default function Templates() {
  return (
    <Stack>
      <Title order={2}>Шаблоны писем</Title>
      <Card withBorder padding="lg">
        <Text c="dimmed">
          Здесь будет CRUD для шаблонов и WYSIWYG-редактор. API готов: GET/POST /templates.
        </Text>
      </Card>
    </Stack>
  );
}
