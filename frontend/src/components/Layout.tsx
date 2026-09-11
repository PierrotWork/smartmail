import { AppShell, NavLink, Title, Group, Button } from "@mantine/core";
import { Outlet, NavLink as RouterNavLink, useNavigate } from "react-router-dom";
import {
  IconDashboard,
  IconUsers,
  IconMailFast,
  IconTemplate,
  IconLogout,
} from "@tabler/icons-react";

export default function Layout() {
  const navigate = useNavigate();

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: "sm" }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Title order={4}>SmartMail Campaigns</Title>
          <Button
            variant="subtle"
            leftSection={<IconLogout size={16} />}
            onClick={logout}
          >
            Выйти
          </Button>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        <NavLink
          component={RouterNavLink}
          to="/"
          label="Дашборд"
          leftSection={<IconDashboard size={18} />}
          end
        />
        <NavLink
          component={RouterNavLink}
          to="/clients"
          label="Клиенты"
          leftSection={<IconUsers size={18} />}
        />
        <NavLink
          component={RouterNavLink}
          to="/templates"
          label="Шаблоны"
          leftSection={<IconTemplate size={18} />}
        />
        <NavLink
          component={RouterNavLink}
          to="/campaigns"
          label="Рассылки"
          leftSection={<IconMailFast size={18} />}
        />
      </AppShell.Navbar>

      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
