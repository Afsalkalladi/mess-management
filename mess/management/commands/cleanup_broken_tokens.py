from django.core.management.base import BaseCommand
from mess.models import StaffToken


class Command(BaseCommand):
    help = 'Clean up broken staff tokens with empty token_hash'

    def handle(self, *args, **options):
        # Find tokens with empty or null token_hash
        broken_tokens = StaffToken.objects.filter(
            token_hash__in=['', None]
        )
        
        count = broken_tokens.count()
        
        if count > 0:
            self.stdout.write(f'Found {count} broken tokens. Deleting...')
            broken_tokens.delete()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Deleted {count} broken tokens')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ No broken tokens found')
            )
        
        # Show remaining valid tokens
        valid_tokens = StaffToken.objects.exclude(
            token_hash__in=['', None]
        )
        
        self.stdout.write(f'\n📊 Valid tokens remaining: {valid_tokens.count()}')
        
        for token in valid_tokens:
            status = '✅ Active' if token.active else '❌ Inactive'
            self.stdout.write(f'  • {token.label}: {status}')
