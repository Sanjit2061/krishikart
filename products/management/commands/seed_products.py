from django.core.management.base import BaseCommand
from accounts.models import User
from products.models import Category, Product


class Command(BaseCommand):
    help = 'Seeds the database with sample categories and products'

    def handle(self, *args, **options):
        farmer, created = User.objects.get_or_create(
            username='demo_farmer',
            defaults={
                'email': 'farmer@krishikart.com',
                'is_farmer': True,
                'first_name': 'Ram',
                'last_name': 'Thapa',
            }
        )
        if created:
            farmer.set_password('farmer12345')
            farmer.save()
            self.stdout.write(self.style.SUCCESS('Created demo farmer: demo_farmer / farmer12345'))

        categories_data = [
            {'name': 'Vegetables', 'icon': 'fa-carrot'},
            {'name': 'Fruits', 'icon': 'fa-apple-alt'},
            {'name': 'Dairy', 'icon': 'fa-cheese'},
            {'name': 'Grains', 'icon': 'fa-wheat-alt'},
            {'name': 'Honey', 'icon': 'fa-jar'},
            {'name': 'Spices', 'icon': 'fa-pepper-hot'},
        ]

        categories = {}
        for cat in categories_data:
            obj, _ = Category.objects.get_or_create(name=cat['name'], defaults={'icon': cat['icon']})
            categories[cat['name']] = obj

        products_data = [
            {'name': 'Fresh Tomatoes', 'category': 'Vegetables', 'price': 60, 'old_price': 80, 'unit': 'kg',
             'organic': True, 'featured': True,
             'image': 'https://images.unsplash.com/photo-1592841200221-a6898f307baa?w=500'},
            {'name': 'Green Spinach', 'category': 'Vegetables', 'price': 40, 'old_price': None, 'unit': 'kg',
             'organic': True, 'featured': False,
             'image': 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=500'},
            {'name': 'Cauliflower', 'category': 'Vegetables', 'price': 45, 'old_price': None, 'unit': 'kg',
             'organic': False, 'featured': False,
             'image': 'https://images.unsplash.com/photo-1568584711271-6c928a3c3bce?w=500'},
            {'name': 'Farm Potatoes', 'category': 'Vegetables', 'price': 35, 'old_price': None, 'unit': 'kg',
             'organic': False, 'featured': True,
             'image': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=500'},
            {'name': 'Sweet Mangoes', 'category': 'Fruits', 'price': 150, 'old_price': 180, 'unit': 'kg',
             'organic': True, 'featured': True,
             'image': 'https://images.unsplash.com/photo-1601493700631-2b16ec4b4716?w=500'},
            {'name': 'Nepali Apples', 'category': 'Fruits', 'price': 220, 'old_price': None, 'unit': 'kg',
             'organic': False, 'featured': False,
             'image': 'https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=500'},
            {'name': 'Fresh Bananas', 'category': 'Fruits', 'price': 70, 'old_price': None, 'unit': 'dozen',
             'organic': True, 'featured': False,
             'image': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=500'},
            {'name': 'Farm Fresh Milk', 'category': 'Dairy', 'price': 90, 'old_price': None, 'unit': 'liter',
             'organic': True, 'featured': True,
             'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=500'},
            {'name': 'Homemade Curd', 'category': 'Dairy', 'price': 65, 'old_price': None, 'unit': 'kg',
             'organic': False, 'featured': False,
             'image': 'https://images.unsplash.com/photo-1571212515416-fef01fc43637?w=500'},
            {'name': 'Basmati Rice', 'category': 'Grains', 'price': 180, 'old_price': 200, 'unit': 'kg',
             'organic': False, 'featured': True,
             'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=500'},
            {'name': 'Organic Wheat Flour', 'category': 'Grains', 'price': 75, 'old_price': None, 'unit': 'kg',
             'organic': True, 'featured': False,
             'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500'},
            {'name': 'Pure Mountain Honey', 'category': 'Honey', 'price': 650, 'old_price': 750, 'unit': 'kg',
             'organic': True, 'featured': True,
             'image': 'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=500'},
        ]

        for p in products_data:
            Product.objects.get_or_create(
                name=p['name'],
                defaults={
                    'farmer': farmer,
                    'category': categories[p['category']],
                    'description': f"Fresh, high quality {p['name'].lower()} sourced directly from local farms.",
                    'price': p['price'],
                    'old_price': p['old_price'],
                    'unit': p['unit'],
                    'stock': 50,
                    'image_url': p['image'],
                    'is_organic': p['organic'],
                    'is_featured': p['featured'],
                    'is_active': True,
                }
            )

        self.stdout.write(self.style.SUCCESS(f'Seeded {len(categories_data)} categories and {len(products_data)} products!'))