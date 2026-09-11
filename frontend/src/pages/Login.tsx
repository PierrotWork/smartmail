import { useState } from "react";
import {
  Button,
  Card,
  Center,
  PasswordInput,
  Stack,
  TextInput,
  Title,
  Text,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { notifications } from "@mantine/notifications";
import { api } from "@/api/client";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      navigate("/");
    } catch (err: any) {
      notifications.show({
        color: "red",
        title: "Ошибка входа",
        message: err?.response?.data?.detail || "Не удалось войти",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Center h="100vh">
      <Card withBorder shadow="sm" padding="xl" w={380}>
        <form onSubmit={submit}>
          <Stack>
            <Title order={3}>SmartMail Campaigns</Title>
            <Text c="dimmed" size="sm">
              Вход в панель управления рассылками
            </Text>
            <TextInput
              label="Email"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              required
            />
            <PasswordInput
              label="Пароль"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
            />
            <Button type="submit" loading={loading} fullWidth>
              Войти
            </Button>
          </Stack>
        </form>
      </Card>
    </Center>
  );
}
