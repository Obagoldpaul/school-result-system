def normalize_person_name(value):
    return value.strip().title() if value else value


def normalize_email(value):
    return value.strip().lower() if value else value