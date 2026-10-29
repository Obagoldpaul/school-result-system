import re
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from students.models import Student


class Command(BaseCommand):
    help = (
        "Preview or update existing admission numbers to include "
        "the registration year."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=timezone.localdate().year,
            help="Year to insert into admission numbers (default: current year).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the changes. Without this flag, the command only previews.",
        )

    def handle(self, *args, **options):
        year = options["year"]
        apply_changes = options["apply"]

        if year < 2000 or year > 9999:
            raise CommandError("Please provide a valid four-digit year.")

        students = list(
            Student.objects.select_related(
                "user",
                "user__school",
            ).order_by("pk")
        )

        existing_numbers = defaultdict(list)

        for student in students:
            number = (student.admission_number or "").strip().casefold()
            existing_numbers[number].append(student.pk)

        changes = []
        skipped = Counter()
        proposed_targets = defaultdict(list)

        for student in students:
            school = getattr(student.user, "school", None)

            if school is None or not school.code:
                skipped["missing school or school code"] += 1
                continue

            old_number = (student.admission_number or "").strip()
            school_code = school.code.upper()

            # Only accept the existing production format:
            # SCHOOLCODE-STU-NNN
            old_pattern = re.compile(
                rf"^{re.escape(school_code)}-STU-(\d+)$",
                re.IGNORECASE,
            )

            # Do not rewrite numbers that already contain a year.
            year_pattern = re.compile(
                rf"^{re.escape(school_code)}-\d{{4}}-STU-\d+$",
                re.IGNORECASE,
            )

            if year_pattern.fullmatch(old_number):
                skipped["already contains a year"] += 1
                continue

            match = old_pattern.fullmatch(old_number)

            if not match:
                skipped["does not match the expected format"] += 1
                continue

            sequence = match.group(1)
            new_number = f"{school_code}-{year}-STU-{sequence}"

            if len(new_number) > Student._meta.get_field(
                "admission_number"
            ).max_length:
                skipped["proposed number exceeds field length"] += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"TOO LONG | Student ID {student.pk} | "
                        f"{old_number} -> {new_number}"
                    )
                )
                continue

            changes.append(
                {
                    "student_id": student.pk,
                    "old_number": old_number,
                    "new_number": new_number,
                }
            )
            proposed_targets[new_number.casefold()].append(student.pk)

        conflicts = []

        # Detect proposed numbers that would collide with one another.
        for target, student_ids in proposed_targets.items():
            if len(student_ids) > 1:
                conflicts.append(
                    f"Multiple students would receive {target}: {student_ids}"
                )

        # Detect collisions with numbers already in the database.
        changing_ids = {item["student_id"] for item in changes}

        for item in changes:
            target_key = item["new_number"].casefold()

            for existing_id in existing_numbers.get(target_key, []):
                if existing_id != item["student_id"]:
                    conflicts.append(
                        f"{item['new_number']} already belongs to "
                        f"student ID {existing_id}; proposed for "
                        f"student ID {item['student_id']}."
                    )

        self.stdout.write(f"Year: {year}")
        self.stdout.write(f"Students inspected: {len(students)}")
        self.stdout.write(f"Proposed changes: {len(changes)}")

        for item in changes:
            self.stdout.write(
                f"Student ID {item['student_id']}: "
                f"{item['old_number']} -> {item['new_number']}"
            )

        if skipped:
            self.stdout.write("\nSkipped records:")

            for reason, count in sorted(skipped.items()):
                self.stdout.write(f"  {reason}: {count}")

        if conflicts:
            self.stdout.write(
                self.style.ERROR(
                    f"\nConflicts found: {len(conflicts)}"
                )
            )

            for conflict in conflicts:
                self.stdout.write(self.style.ERROR(f"  {conflict}"))

            raise CommandError(
                "Conflicts must be resolved before any changes can be applied."
            )

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "\nPREVIEW ONLY: no database records were changed. "
                    "Use --apply only after reviewing this output."
                )
            )
            return

        if not changes:
            self.stdout.write("No eligible admission numbers need updating.")
            return

        with transaction.atomic():
            # Re-fetch and verify each original value before saving.
            for item in changes:
                student = Student.objects.select_for_update().get(
                    pk=item["student_id"]
                )

                if (student.admission_number or "").strip() != item["old_number"]:
                    raise CommandError(
                        f"Student ID {student.pk} changed after preview. "
                        "No updates were committed; run the preview again."
                    )

                student.admission_number = item["new_number"]
                student.save(update_fields=["admission_number"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated {len(changes)} admission numbers."
            )
        )
