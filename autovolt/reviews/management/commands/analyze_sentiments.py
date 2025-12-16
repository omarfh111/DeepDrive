from django.core.management.base import BaseCommand
from reviews.models import Commentaire
from django.utils import timezone


class Command(BaseCommand):
    help = 'Analyze sentiment for all comments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reanalyze',
            action='store_true',
            help='Re-analyze comments that already have sentiment data',
        )

    def handle(self, *args, **options):
        if options['reanalyze']:
            comments = Commentaire.objects.filter(is_approved=True)
            self.stdout.write('Re-analyzing all approved comments...')
        else:
            comments = Commentaire.objects.filter(
                is_approved=True,
                sentiment_label__isnull=True
            )
            self.stdout.write('Analyzing comments without sentiment data...')

        total = comments.count()
        self.stdout.write(f'Found {total} comments to analyze')

        for i, comment in enumerate(comments, 1):
            try:
                result = comment.analyze_sentiment()
                self.stdout.write(
                    f'[{i}/{total}] Analyzed: {comment.id} - '
                    f'{result["sentiment"]} ({result["confidence"]:.2f})'
                )
            except Exception as e:
                self.stderr.write(f'Error analyzing comment {comment.id}: {e}')

        self.stdout.write(self.style.SUCCESS(f'Successfully analyzed {total} comments'))