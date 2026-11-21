from django.core.management.base import BaseCommand
from store.models import Category, Product


class Command(BaseCommand):
    help = "Create a small, repeatable NOVA MARKET catalogue for local development."

    products = [
        ("Audio", "Halo Wireless Headphones", "A premium everyday listening experience with adaptive noise control.", "NM-AUDIO-001", "189.00", "229.00", 24, True),
        ("Workspace", "Arc Desk Lamp", "A sculptural aluminum lamp with a warm, adjustable glow.", "NM-WORK-001", "129.00", None, 18, True),
        ("Travel", "Atlas Carryall", "Weather-resistant carryall with considered pockets for modern travel.", "NM-TRAVEL-001", "164.00", "198.00", 12, True),
        ("Home", "Forma Ceramic Set", "Hand-finished ceramic vessels designed for everyday rituals.", "NM-HOME-001", "86.00", None, 31, False),
        ("Wellness", "Still Essential Oil Set", "Three quietly layered botanical blends for slow evenings.", "NM-WELL-001", "54.00", None, 40, False),
        ("Workspace", "Terra Notebook", "Bound recycled paper with a tactile linen cover.", "NM-WORK-002", "28.00", None, 60, False),
    ]

    def handle(self, *args, **options):
        for category_name, name, description, sku, price, compare_at_price, stock, featured in self.products:
            category, _ = Category.objects.get_or_create(name=category_name)
            Product.objects.update_or_create(
                sku=sku,
                defaults={
                    "category": category, "name": name, "description": description,
                    "price": price, "compare_at_price": compare_at_price,
                    "stock_quantity": stock, "is_featured": featured, "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS("Catalogue seeded successfully."))
