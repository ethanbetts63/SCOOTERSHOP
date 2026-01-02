import os
from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Exports Motorcycle, MotorcycleImage, and MotorcycleCondition models to separate JSON files.'

    MODELS_TO_EXPORT = [
        'inventory.Motorcycle',
        'inventory.MotorcycleImage',
        'inventory.MotorcycleCondition',
    ]
    OUTPUT_DIR = 'scooter_shop_archive'

    def handle(self, *args, **kwargs):
        """
        Handles the execution of the command.
        """
        # Ensure the output directory exists
        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR)

        self.stdout.write(self.style.SUCCESS(f"Starting export of inventory models..."))

        for model_label in self.MODELS_TO_EXPORT:
            # We need to get the actual model name, which is lowercase
            app_label, model_name = model_label.split('.')
            output_filename = f"{app_label}.{model_name.lower()}.json"
            output_filepath = os.path.join(self.OUTPUT_DIR, output_filename)

            self.stdout.write(f"  - Exporting {model_label} to {output_filepath}...")

            try:
                # Open the file to write the output of dumpdata
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    call_command('dumpdata', model_label, indent=2, stdout=f)
                self.stdout.write(self.style.SUCCESS(f"    Successfully exported {model_label}."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"    Failed to export {model_label}.\n    Error: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"\nExport complete. Files saved in: {self.OUTPUT_DIR}"))
