from django.apps import AppConfig


class ConfigConfig(AppConfig):
    name = 'config'

    def ready(self):
        # --- Ensure admin user exists on every startup (robust for ephemeral DB) ---
        try:
            from django.contrib.auth.models import User
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='Admin123!'
                )
        except Exception:
            # Ignore errors if DB not ready (e.g. during migrate/collectstatic)
            pass
