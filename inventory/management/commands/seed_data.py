import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from inventory.models import Motorcycle, FeaturedMotorcycle, MotorcycleCondition

# Sample data for creating realistic motorcycles
BIKE_DATA = {
    "SYM": ["Orbit", "Jet", "Fiddle", "Symphony"],
    "Honda": ["Dio", "PCX", "ADV", "Click"],
    "Yamaha": ["NMAX", "Mio", "Aerox", "XMAX"],
    "Vespa": ["Primavera", "Sprint", "GTS Super"],
    "Segway": ["E110A", "C80"],
}


class Command(BaseCommand):
    """
    A custom Django management command to seed the database with test data.
    This helps in setting up a development environment with realistic data.

    Example usage:
    - python manage.py seed_data (Clears and creates all data types)
    - python manage.py seed_data --type motorcycles --count 20 (Creates 20 motorcycles)
    - python manage.py seed_data --type featured (Only seeds featured motorcycles)
    - python manage.py seed_data --no-clear (Appends data without deleting old data)
    """

    help = "Seeds the database with initial or test data for the inventory app."

    def add_arguments(self, parser):
        """Adds command-line arguments to the command."""
        parser.add_argument(
            "--type",
            type=str,
            help='Specify data to seed ("all", "motorcycles", "featured").',
            default="all",
        )
        parser.add_argument(
            "--count", type=int, help="Number of motorcycles to create.", default=15
        )
        parser.add_argument(
            "--no-clear",
            action="store_true",
            help="Do not clear existing data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        """The main logic for the command."""
        should_clear = not options["no_clear"]
        data_type = options["type"]
        count = options["count"]

        self.stdout.write(self.style.SUCCESS("--- Starting Data Seeding Operation ---"))

        # The order is important: Conditions -> Motorcycles -> Featured
        self._seed_conditions()

        if data_type in ["all", "motorcycles"]:
            self._seed_motorcycles(clear=should_clear, count=count)

        if data_type in ["all", "featured"]:
            self._seed_featured_motorcycles(clear=should_clear)

        self.stdout.write(self.style.SUCCESS("--- Data Seeding Operation Finished ---"))

    def _seed_conditions(self):
        """Ensures the basic MotorcycleCondition objects exist."""
        self.stdout.write(
            self.style.HTTP_INFO("\nChecking/Seeding Motorcycle Conditions...")
        )
        for name in ["New", "Used", "Demo"]:
            obj, created = MotorcycleCondition.objects.get_or_create(
                name=name.lower(), defaults={"display_name": name}
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  - Created '{obj.display_name}' condition.")
                )

    def _seed_motorcycles(self, clear=True, count=15):
        """Handles the seeding of Motorcycle instances."""
        self.stdout.write(self.style.HTTP_INFO(f"\nSeeding {count} Motorcycles..."))
        if clear:
            # Be careful with this in production!
            deleted_count, _ = Motorcycle.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"  - Cleared {deleted_count} existing motorcycles.")
            )

        used_condition = MotorcycleCondition.objects.get(name="used")
        new_condition = MotorcycleCondition.objects.get(name="new")

        created_count = 0
        for i in range(count):
            brand = random.choice(list(BIKE_DATA.keys()))
            model = random.choice(BIKE_DATA[brand])
            year = random.randint(2015, 2024)
            is_used = random.choice(
                [True, True, False]
            )  # Make it more likely to be used

            bike = Motorcycle.objects.create(
                title=f"{year} {brand} {model}",
                brand=brand,
                model=model,
                year=year,
                price=random.randint(1500, 7500),
                condition="used" if is_used else "new",
                status="for_sale",
                odometer=random.randint(2000, 50000) if is_used else 0,
                engine_size=random.choice([50, 110, 125, 150, 300]),
                transmission=random.choice(["automatic", "manual"]),
                stock_number=f"TEST-{1000 + i}",
                description=f"A fantastic {'used' if is_used else 'new'} {brand} {model}, perfect for city cruising.",
            )

            # Add the corresponding ManyToMany condition
            if is_used:
                bike.conditions.add(used_condition)
            else:
                bike.conditions.add(new_condition)

            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  - Successfully created {created_count} new motorcycles."
            )
        )

    def _seed_featured_motorcycles(self, clear=True):
        """Handles the seeding of FeaturedMotorcycle instances."""
        self.stdout.write(self.style.HTTP_INFO("\nSeeding Featured Motorcycles..."))

        if clear:
            deleted_count, _ = FeaturedMotorcycle.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    f"  - Cleared {deleted_count} existing featured motorcycles."
                )
            )

        self._create_featured_set("new", 5)
        self._create_featured_set("used", 10)

    def _create_featured_set(self, category, count):
        """Helper to create a set of featured motorcycles for a category."""
        self.stdout.write(
            f"  - Creating up to {count} featured '{category}' motorcycles..."
        )

        condition_filter = Q(condition=category) | Q(conditions__name__iexact=category)
        existing_featured_ids = FeaturedMotorcycle.objects.values_list(
            "motorcycle_id", flat=True
        )

        eligible_bikes = (
            Motorcycle.objects.filter(condition_filter)
            .exclude(pk__in=existing_featured_ids)
            .distinct()
        )

        if eligible_bikes.count() < count:
            count = eligible_bikes.count()

        if count == 0:
            self.stdout.write(
                self.style.WARNING(
                    f"    - No available '{category}' motorcycles to feature."
                )
            )
            return

        bikes_to_feature = random.sample(list(eligible_bikes), count)

        created_count = 0
        for index, bike in enumerate(bikes_to_feature):
            FeaturedMotorcycle.objects.create(
                motorcycle=bike, category=category, order=index + 1
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"    - Successfully created {created_count} new '{category}' featured instances."
            )
        )
