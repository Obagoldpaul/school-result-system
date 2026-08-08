from academics.models import SchoolSettings


class BrandingService:

    @staticmethod
    def settings():

        return SchoolSettings.load()