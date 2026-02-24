from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='TestResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test_case', models.CharField(max_length=255)),
                ('url', models.URLField(max_length=2048)),
                ('passed', models.BooleanField(default=False)),
                ('comment', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'Test Result',
                'verbose_name_plural': 'Test Results',
                'db_table': 'testing',
            },
        ),
        migrations.CreateModel(
            name='ListingData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=512)),
                ('price', models.CharField(blank=True, max_length=100)),
                ('image_url', models.URLField(blank=True, max_length=2048)),
                ('listing_url', models.URLField(blank=True, max_length=2048)),
                ('scraped_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Listing',
                'verbose_name_plural': 'Listings',
                'db_table': 'listing_data',
            },
        ),
        migrations.CreateModel(
            name='SuggestionData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=512)),
                ('search_query', models.CharField(max_length=255)),
                ('captured_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Suggestion',
                'verbose_name_plural': 'Suggestions',
                'db_table': 'suggestion_data',
            },
        ),
        migrations.CreateModel(
            name='NetworkLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=2048)),
                ('method', models.CharField(choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE'), ('PATCH', 'PATCH'), ('OPTIONS', 'OPTIONS')], default='GET', max_length=10)),
                ('status_code', models.IntegerField(blank=True, null=True)),
                ('resource_type', models.CharField(blank=True, max_length=50)),
                ('captured_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Network Log',
                'verbose_name_plural': 'Network Logs',
                'db_table': 'network_logs',
            },
        ),
        migrations.CreateModel(
            name='ConsoleLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error'), ('DEBUG', 'Debug')], default='INFO', max_length=20)),
                ('message', models.TextField()),
                ('source', models.CharField(blank=True, max_length=512)),
                ('captured_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Console Log',
                'verbose_name_plural': 'Console Logs',
                'db_table': 'console_logs',
            },
        ),
    ]
