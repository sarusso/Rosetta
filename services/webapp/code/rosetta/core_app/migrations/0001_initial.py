# Generated by Django 2.2.1 on 2020-05-28 15:12

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Computing',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='Computing Name')),
                ('type', models.CharField(max_length=255, verbose_name='Computing Type')),
                ('requires_sys_conf', models.BooleanField(default=False)),
                ('requires_user_conf', models.BooleanField(default=False)),
                ('requires_user_keys', models.BooleanField(default=False)),
                ('supports_docker', models.BooleanField(default=False)),
                ('supports_singularity', models.BooleanField(default=False)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Container',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='Container Name')),
                ('image', models.CharField(max_length=255, verbose_name='Container image')),
                ('type', models.CharField(max_length=36, verbose_name='Container type')),
                ('registry', models.CharField(max_length=255, verbose_name='Container registry')),
                ('ports', models.CharField(blank=True, max_length=36, null=True, verbose_name='Container ports')),
                ('supports_dynamic_ports', models.BooleanField(default=False)),
                ('supports_user_auth', models.BooleanField(default=False)),
                ('supports_pass_auth', models.BooleanField(default=False)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tid', models.CharField(blank=True, max_length=64, null=True, verbose_name='Task ID')),
                ('name', models.CharField(max_length=36, verbose_name='Task name')),
                ('status', models.CharField(blank=True, max_length=36, null=True, verbose_name='Task status')),
                ('created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Created on')),
                ('pid', models.IntegerField(blank=True, null=True, verbose_name='Task pid')),
                ('port', models.IntegerField(blank=True, null=True, verbose_name='Task port')),
                ('ip', models.CharField(blank=True, max_length=36, null=True, verbose_name='Task ip address')),
                ('tunnel_port', models.IntegerField(blank=True, null=True, verbose_name='Task tunnel port')),
                ('extra_binds', models.CharField(blank=True, max_length=4096, null=True, verbose_name='Extra binds')),
                ('auth_user', models.CharField(blank=True, max_length=36, null=True, verbose_name='Task auth user')),
                ('auth_pass', models.CharField(blank=True, max_length=36, null=True, verbose_name='Task auth pass')),
                ('access_method', models.CharField(blank=True, max_length=36, null=True, verbose_name='Task access method')),
                ('computing_options', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('computing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core_app.Computing')),
                ('container', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core_app.Container')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('timezone', models.CharField(default='UTC', max_length=36, verbose_name='User Timezone')),
                ('authtoken', models.CharField(blank=True, max_length=36, null=True, verbose_name='User auth token')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='LoginToken',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('token', models.CharField(max_length=36, verbose_name='Login token')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='KeyPair',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('private_key_file', models.CharField(max_length=4096, verbose_name='Private key file')),
                ('public_key_file', models.CharField(max_length=4096, verbose_name='Public key file')),
                ('default', models.BooleanField(default=False, verbose_name='Default keys?')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ComputingUserConf',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('computing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core_app.Computing')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ComputingSysConf',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('computing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core_app.Computing')),
            ],
        ),
    ]
