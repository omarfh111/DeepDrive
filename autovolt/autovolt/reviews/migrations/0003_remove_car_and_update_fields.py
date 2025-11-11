# Generated manually to remove Car model and update fields to match UML

from django.db import migrations, models
import django.utils.timezone


def populate_date_joined(apps, schema_editor):
    """Populate date_joined with date_review value for existing reviews"""
    Review = apps.get_model('reviews', 'Review')
    for review in Review.objects.all():
        # date_review is still DateTimeField at this point, so we can use it directly
        if review.date_review:
            review.date_joined = review.date_review
        else:
            review.date_joined = django.utils.timezone.now()
        review.save(update_fields=['date_joined'])


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0002_review_image'),
    ]

    operations = [
        # Remove car foreign key constraint first
        migrations.RemoveConstraint(
            model_name='review',
            name='unique_user_car_review',
        ),
        # Remove car foreign key field
        migrations.RemoveField(
            model_name='review',
            name='car',
        ),
        # Remove date_updated from review
        migrations.RemoveField(
            model_name='review',
            name='date_updated',
        ),
        # Remove date_updated from commentaire
        migrations.RemoveField(
            model_name='commentaire',
            name='date_updated',
        ),
        # Add date_joined to review (nullable first, then populate, then make non-null)
        migrations.AddField(
            model_name='review',
            name='date_joined',
            field=models.DateTimeField(null=True, verbose_name='date_joined'),
        ),
        # Populate date_joined with existing data
        migrations.RunPython(populate_date_joined, migrations.RunPython.noop),
        # Make date_joined non-nullable and add auto_now_add
        migrations.AlterField(
            model_name='review',
            name='date_joined',
            field=models.DateTimeField(auto_now_add=True, verbose_name='date_joined'),
        ),
        # Change date_review from DateTimeField to DateField
        migrations.AlterField(
            model_name='review',
            name='date_review',
            field=models.DateField(auto_now_add=True, verbose_name='DateReview'),
        ),
        # Change date_commentaire from DateTimeField to DateField
        migrations.AlterField(
            model_name='commentaire',
            name='date_commentaire',
            field=models.DateField(auto_now_add=True, verbose_name='DateCommentaire'),
        ),
        # Update Meta options for review (remove constraint reference)
        migrations.AlterModelOptions(
            name='review',
            options={'ordering': ['-date_joined'], 'verbose_name': 'Avis', 'verbose_name_plural': 'Avis'},
        ),
        # Delete Car model
        migrations.DeleteModel(
            name='Car',
        ),
    ]

