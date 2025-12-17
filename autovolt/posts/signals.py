from decimal import Decimal
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Post
from .ml_model import predict_price_and_label


@receiver(pre_save, sender=Post)
def set_price_prediction(sender, instance: Post, **kwargs):
    """
    Auto-fill:
      - predicted_price (Decimal, 0 decimals)
      - offer_label ("OVERPRICED" | "NORMAL" | "GOOD_DEAL")
    before saving a Post.
    """

    # Required fields (match your models.py exactly)
    if not all([
        instance.year,
        instance.kilometrage,
        instance.marque,
        instance.modele,
        instance.price,
    ]):
        return

    try:
        pred, label = predict_price_and_label(
            annee=int(instance.year),               
            kilometrage=float(instance.kilometrage),
            marque=str(instance.marque),
            modele=str(instance.modele),
            seller_price=float(instance.price),
        )

        # predicted_price is DecimalField(decimal_places=0)
        instance.predicted_price = Decimal(str(round(pred)))
        instance.offer_label = label

    except Exception as e:
        # Never block saving
        print(f"[PRICE_MODEL] failed for Post(id={instance.pk}): {e!r}")
